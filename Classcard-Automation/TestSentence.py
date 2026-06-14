import re
import time
import random
import threading
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchWindowException


GO_RESULT_SELECTOR = 'a.btn-go-result'

# 진단용: True면 문제별 파싱/클릭 결과를 터미널에 출력
DEBUG = False

# 테스트 목표 점수(0~100). 이 점수가 나오도록 일부러 틀릴 문항 수를 자동 계산한다.
# 예) 90 → 10%만 일부러 틀림, 100 → 다 맞음.
# (정답 매칭 실패가 있으면 실제 점수는 이보다 더 낮게 나올 수 있음)
TARGET_SCORE = 100

# 테스트 '이탈 감지' 우회: 탭/창 포커스를 잃어도 항상 보이는/포커스된 상태로 위장.
_ANTI_BLUR_JS = r'''
(function(){
  try {
    Object.defineProperty(document, 'hidden', {configurable:true, get:function(){return false;}});
    Object.defineProperty(document, 'visibilityState', {configurable:true, get:function(){return 'visible';}});
    Object.defineProperty(document, 'webkitHidden', {configurable:true, get:function(){return false;}});
    Object.defineProperty(document, 'webkitVisibilityState', {configurable:true, get:function(){return 'visible';}});
  } catch(e){}
  try { document.hasFocus = function(){ return true; }; } catch(e){}
  function blocker(e){
    var t = e.type;
    if (t === 'visibilitychange' || t === 'webkitvisibilitychange' ||
        t === 'mozvisibilitychange' || t === 'msvisibilitychange' || t === 'pagehide') {
      e.stopImmediatePropagation(); return;
    }
    if ((t === 'blur' || t === 'focusout') && (e.target === window || e.target === document)) {
      e.stopImmediatePropagation();
    }
  }
  var evts = ['visibilitychange','webkitvisibilitychange','mozvisibilitychange',
              'msvisibilitychange','pagehide','blur','focusout'];
  evts.forEach(function(ev){
    window.addEventListener(ev, blocker, true);
    document.addEventListener(ev, blocker, true);
  });
  try { window.onblur = null; } catch(e){}
})();
'''


def suppress_leave_detection(driver):
    """현재 페이지에 '이탈 감지 우회' 스크립트를 주입."""
    try:
        driver.execute_script(_ANTI_BLUR_JS)
    except NoSuchWindowException:
        raise
    except Exception:
        pass


# ===== 한글/영어 정규화 =====
_WS = re.compile(r'[\s​‌‍‎‏﻿]')


def normalize_kor(text):
    """한글 프롬프트 비교용: NFKC + 모든 공백/제로폭 문자 제거."""
    text = unicodedata.normalize('NFKC', text or '')
    return _WS.sub('', text)


def strip_parens(text):
    """`(...)` 괄호 묶음 제거 (괄호 표기가 한쪽에만 있는 경우 폴백용)."""
    return re.sub(r'\([^)]*\)', '', text or '')


def norm_en(token):
    """영어 토큰 ↔ 버튼 텍스트 비교용: 소문자 + 영숫자만 남김.
    (따옴표 종류, 대소문자, 구두점 차이를 흡수: I'm/I'm → im)"""
    return re.sub(r'[^a-z0-9]', '', (token or '').lower())


def build_maps(answer_dict):
    """answer_dict = {한글(back): 영어(front)} → 정규화 맵 2종.
    m: 한글 그대로,  mnp: 괄호 제거 버전(폴백)."""
    m, mnp = {}, {}
    for back, front in answer_dict.items():
        if not back:
            continue
        m[normalize_kor(back)] = front
        mnp[normalize_kor(strip_parens(back))] = front
    print(f"[문장 테스트] 매칭 데이터 로드 완료 (카드 {len(answer_dict)}개)")
    return m, mnp


def match_english(prompt_raw, m, mnp):
    """한글 프롬프트로 영어 정답 문장 조회. 실패 시 괄호 제거 폴백."""
    p = normalize_kor(prompt_raw)
    if p in m:
        return m[p]
    pnp = normalize_kor(strip_parens(prompt_raw))
    if pnp in mnp:
        return mnp[pnp]
    return None


# 현재 보이는 문제(.flip-card.showing)만 읽는다.
_READ_CARD_JS = r'''
var card = document.querySelector('.flip-card.showing');
if (!card) return { found: false };

var qid = '';
var qi = card.querySelector('input[name="test_question[]"]');
if (qi) qid = qi.value;

var flipped = card.classList.contains('flip');

var prompt = '';
var fh = card.querySelector('.flip-card-front .front-hidden');
if (fh) prompt = (fh.textContent || '').trim();

var words = card.querySelectorAll('.test-sentence-words a.btn').length;
var placed = card.querySelectorAll('.test-sentence-input span').length;

return { found: true, qid: qid, flipped: flipped, prompt: prompt,
         words: words, placed: placed };
'''


def read_card(driver):
    """returns dict {qid, flipped, prompt, words, placed} 또는 None."""
    try:
        data = driver.execute_script(_READ_CARD_JS)
    except NoSuchWindowException:
        raise
    except Exception:
        return None
    if not data or not data.get('found'):
        return None
    return {
        'qid': data.get('qid') or '',
        'flipped': bool(data.get('flipped')),
        'prompt': (data.get('prompt') or '').strip(),
        'words': int(data.get('words') or 0),
        'placed': int(data.get('placed') or 0),
    }


def _cdp_click(driver, element):
    """CDP Input.dispatchMouseEvent로 '진짜 입력(isTrusted=true)' 클릭을 보낸다.
    이 스크램블 버튼은 합성 click(JS/Selenium .click()/jQuery trigger)을 모두 무시하고
    오직 trusted 마우스 이벤트에만 반응하기 때문."""
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center', inline:'center'});", element
    )
    pos = driver.execute_script(
        "var r = arguments[0].getBoundingClientRect();"
        "return {x: r.left + r.width/2, y: r.top + r.height/2};",
        element,
    )
    x, y = pos['x'], pos['y']
    driver.execute_cdp_cmd('Input.dispatchMouseEvent',
                           {'type': 'mouseMoved', 'x': x, 'y': y, 'buttons': 0})
    driver.execute_cdp_cmd('Input.dispatchMouseEvent',
                           {'type': 'mousePressed', 'x': x, 'y': y,
                            'button': 'left', 'buttons': 1, 'clickCount': 1})
    driver.execute_cdp_cmd('Input.dispatchMouseEvent',
                           {'type': 'mouseReleased', 'x': x, 'y': y,
                            'button': 'left', 'buttons': 0, 'clickCount': 1})


def click_word(driver, token):
    """현재 showing 카드에서 아직 안 클릭된 스크램블 버튼 중 token과 맞는 버튼을 CDP 클릭.
    매칭 우선순위: 정확 일치(대소문자 구분) → 대소문자 무시 → 영숫자만.
    (한 문장에 'The'/'the'처럼 대소문자만 다른 단어가 함께 나올 때 엉뚱한 버튼을 집지 않도록.)
    성공 True."""
    try:
        btns = driver.find_elements(
            By.CSS_SELECTOR, '.flip-card.showing .test-sentence-words a.btn'
        )
    except NoSuchWindowException:
        raise
    except Exception:
        return False

    # 아직 클릭 안 된 버튼만 (raw 텍스트 보존)
    cands = []
    for b in btns:
        try:
            cls = (b.get_attribute('class') or '').split()
            if 'clicked' in cls:
                continue
            raw = (b.get_attribute('textContent') or b.text or '').strip()
            cands.append((b, raw))
        except NoSuchWindowException:
            raise
        except Exception:
            continue

    tok = token.strip()
    tok_low = tok.lower()
    tok_norm = norm_en(tok)

    target = None
    for b, raw in cands:                       # 1) 정확 일치 (대소문자 구분)
        if raw == tok:
            target = b
            break
    if target is None:
        for b, raw in cands:                   # 2) 대소문자 무시
            if raw.lower() == tok_low:
                target = b
                break
    if target is None and tok_norm:
        for b, raw in cands:                   # 3) 영숫자만 (따옴표/구두점 차이 흡수)
            if norm_en(raw) == tok_norm:
                target = b
                break

    if target is None:
        return False

    try:
        _cdp_click(driver, target)
    except Exception:
        try:
            target.click()
        except Exception:
            driver.execute_script("arguments[0].click();", target)
    return True


# 진단용: 현재 showing 카드의 스크램블 버튼 텍스트 + clicked 여부 목록.
_LIST_BTNS_JS = r'''
var card = document.querySelector('.flip-card.showing');
if (!card) return [];
var out = [];
var btns = card.querySelectorAll('.test-sentence-words a.btn');
for (var i = 0; i < btns.length; i++) {
  out.push((btns[i].textContent || '').trim() +
           (btns[i].classList.contains('clicked') ? '*' : ''));
}
return out;
'''


def list_buttons(driver):
    try:
        return driver.execute_script(_LIST_BTNS_JS) or []
    except Exception:
        return []


def _press_space(driver):
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
        return True
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def _click(driver, element):
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def _click_exit(driver, timeout=10):
    """'나가기' 버튼 클릭. set 상세로 가는 링크(a[href*="/set/"]) 우선, 없으면 '나가기' 텍스트."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            # 1) set 상세로 가는 '나가기' 링크 (예: <a ... href="/set/27357169/1933584">나가기</a>)
            for a in driver.find_elements(By.CSS_SELECTOR, 'a[href*="/set/"]'):
                try:
                    if a.is_displayed() and '나가기' in (a.text or ''):
                        _click(driver, a)
                        return True
                except Exception:
                    continue
            # 2) 텍스트가 '나가기'인 링크
            for a in driver.find_elements(By.CSS_SELECTOR, 'a'):
                try:
                    if a.is_displayed() and '나가기' in (a.text or ''):
                        _click(driver, a)
                        return True
                except Exception:
                    continue
            # 3) 폴백: set 링크 아무거나
            for a in driver.find_elements(By.CSS_SELECTOR, 'a.btn-primary[href*="/set/"]'):
                try:
                    if a.is_displayed():
                        _click(driver, a)
                        return True
                except Exception:
                    continue
        except NoSuchWindowException:
            raise
        except Exception:
            pass
        time.sleep(0.3)
    return False


def check_end_and_stop(driver, stop_event):
    """결과 화면(btn-go-result '제출 결과 확인')이 보이면 클릭 → '나가기'(set 링크) 클릭으로
    set 상세 화면 복귀 후 stop_event.set(). (단어 테스트와 달리 X 닫기 단계 없음)"""
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, GO_RESULT_SELECTOR)
        visible = [b for b in buttons if b.is_displayed()]
        if not visible:
            return False

        _click(driver, visible[0])  # 제출 결과 확인
        time.sleep(1.0)

        if not _click_exit(driver, timeout=10):  # 나가기 → set 상세
            print("[문장 테스트] '나가기' 버튼을 찾지 못했습니다.")
        time.sleep(0.5)

        stop_event.set()
        return True
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def _count_total(driver):
    try:
        return driver.execute_script(
            "return document.querySelectorAll('.flip-card input[name=\"test_question[]\"]').length;"
        )
    except Exception:
        return None


def _plan_wrong(total):
    """TARGET_SCORE 이상이 나오도록 일부러 틀릴 문항 순번(1-based) 집합.
    틀릴 개수 = floor(total * (100 - TARGET_SCORE) / 100) — 내림이라 점수는 항상 목표 이상."""
    if not total or total <= 0:
        return set()
    n_wrong = int(total * (100 - TARGET_SCORE) / 100.0)
    n_wrong = max(0, min(n_wrong, total))
    if n_wrong == 0:
        return set()
    return set(random.sample(range(1, total + 1), n_wrong))


def parse_english_words(sentence):
    """영어 문장을 토큰으로 분리하되 괄호 묶음 '(...)'은 통째로 한 토큰으로 유지.
    (스크램블이 괄호구를 한 버튼으로 묶어 표시하는 경우 대응)"""
    return re.findall(r'\([^)]*\)|\S+', sentence or '')


def _split_subtokens(token):
    """통째 매칭 실패한 토큰을 괄호/하이픈 기준으로 더 잘게 분해 (부분 클릭용)."""
    if '(' in token and ')' in token:
        subs = []
        for part in re.split(r'(\([^)]*\))', token):
            part = part.strip('()')
            subs.extend(part.split())
        return subs
    if re.search(r'[-–—]', token):
        return [s for s in re.split(r'[-–—]', token) if s]
    return []


def _click_with_retry(driver, token, stop_event):
    """단어가 아직 렌더링(슬라이드-인) 안 됐을 수 있어 잠깐 기다렸다 최대 4회 재시도.
    returns 'stop' | True | False."""
    for _ in range(4):
        if stop_event.is_set():
            return 'stop'
        if click_word(driver, token):
            return True
        if stop_event.wait(timeout=0.35):
            return 'stop'
    return False


def click_token(driver, token, stop_event):
    """토큰 한 개를 클릭. 통째 매칭 실패 시 괄호/하이픈으로 분해해 부분 매칭 클릭.
    returns 'stop' | True(하나라도 클릭) | False(아무것도 못함)."""
    res = _click_with_retry(driver, token, stop_event)
    if res == 'stop' or res is True:
        return res

    subs = _split_subtokens(token)
    if not subs:
        return False

    any_ok = False
    for sub in subs:
        if not norm_en(sub):
            continue
        r = _click_with_retry(driver, sub, stop_event)
        if r == 'stop':
            return 'stop'
        if r:
            any_ok = True
        if stop_event.wait(timeout=0.15):
            return 'stop'
    return any_ok


def click_sentence(driver, english, make_wrong, stop_event):
    """영어 문장을 어순대로 클릭. make_wrong이면 마지막 두 토큰을 바꿔 클릭(오답 유도).
    returns 'stop' (중지) / 'ok'."""
    tokens = parse_english_words(english)

    order = list(range(len(tokens)))
    if make_wrong and len(order) >= 2:
        order[-1], order[-2] = order[-2], order[-1]
        print(f"[문장 테스트] 의도적 오답 (어순 변경): {english!r}")

    dumped = False
    for k in order:
        if stop_event.is_set():
            return 'stop'
        token = tokens[k]
        if not norm_en(token):
            continue  # 순수 구두점 토큰(',' '.' 등) skip

        res = click_token(driver, token, stop_event)
        if res == 'stop':
            return 'stop'

        if DEBUG:
            print(f"[문장 테스트]   '{token}' → {'클릭' if res else '버튼없음'}")
        elif not res:
            print(f"[문장 테스트] 버튼 매칭 실패: {token!r}")
            if not dumped:
                print(f"[문장 테스트]   현재 버튼: {list_buttons(driver)}")
                dumped = True

        if stop_event.wait(timeout=0.25):
            return 'stop'

    return 'ok'


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[문장 테스트] 시작")

    suppress_leave_detection(driver)  # 백그라운드 실행 시 '이탈 감지' 우회

    if not answer_dict:
        print("[문장 테스트] answer_dict 비어있음. 종료")
        return

    m, mnp = build_maps(answer_dict)

    total = _count_total(driver)
    wrong_idx = _plan_wrong(total)
    if DEBUG and total:
        print(f"[문장 테스트] 총 {total}문항 / 일부러 틀릴 순번: {sorted(wrong_idx) or '없음'}")

    flip_attempts = {}      # qid별 SPACE flip 시도 횟수 (씹힘 대비 재시도)
    answered_qids = set()   # 단어 배열 완료한 문제
    answered_count = 0      # 실제로 답한 수 (오답 주입 인덱스)

    last_qid = None         # 진척 없음 감지용
    no_progress = 0

    try:
        while not stop_event.is_set():
            if check_end_and_stop(driver, stop_event):
                break

            q = read_card(driver)
            if q is None:
                if stop_event.wait(timeout=0.3):
                    break
                continue

            qid = q['qid']
            flipped = q['flipped']
            prompt = q['prompt']

            # 진척 없음(같은 qid 반복) 감지 → 과도하면 안전 종료
            if qid and qid == last_qid:
                no_progress += 1
            else:
                no_progress = 0
                last_qid = qid
            if no_progress > 50:
                print("[문장 테스트] 진행이 멈춰 종료합니다 (매칭 실패/UI 변경 가능).")
                break

            # 이미 배열 완료한 문제 → 다음으로 진행
            if qid and qid in answered_qids:
                _press_space(driver)
                if stop_event.wait(timeout=0.6):
                    break
                continue

            # 앞면(한글) → SPACE로 flip.
            # SPACE 입력이 씹힐 수 있어, 뒤집힐 때까지 매 루프 재시도(최대 8회).
            if not flipped:
                n = flip_attempts.get(qid, 0)
                if n < 8:
                    _press_space(driver)
                    flip_attempts[qid] = n + 1
                if stop_event.wait(timeout=0.5):
                    break
                continue

            # 뒷면(단어 배열) → 정답 조회 후 클릭
            english = match_english(prompt, m, mnp)
            if not english:
                print(f"[문장 테스트] 매칭 실패: {prompt!r}")
                answered_qids.add(qid)  # 건너뜀 (해당 문항 오답 처리)
                if stop_event.wait(timeout=0.3):
                    break
                continue

            answered_count += 1
            make_wrong = answered_count in wrong_idx

            if DEBUG:
                print(f"[문장 테스트][{answered_count}] {prompt!r} → {english!r}")

            res = click_sentence(driver, english, make_wrong, stop_event)
            answered_qids.add(qid)
            if res == 'stop':
                break

            if stop_event.wait(timeout=0.5):
                break

    except NoSuchWindowException:
        pass
    except Exception as e:
        if not stop_event.is_set():
            print(f"[문장 테스트] 오류: {e}")
    finally:
        print("[문장 테스트] 종료")
