import os
import re
import json
import time
import random
import difflib
import threading
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchWindowException


GO_RESULT_SELECTOR = 'a.btn-go-result'

# 진단용: True면 문제별 파싱 결과를 터미널에 출력
DEBUG = False

# 테스트 목표 점수(0~100). 이 점수가 나오도록 일부러 틀릴 문항 수를 자동 계산한다.
# 예) 90 → 10%만 일부러 틀림, 100 → 다 맞음.
# (data.json 매칭 실패가 있으면 실제 점수는 이보다 더 낮게 나올 수 있음)
TARGET_SCORE = 90

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

# 매칭용 정규화: 한글/영문 글자만 남김 (숫자/공백/구두점 제거).
# 프롬프트 "1. 끌어서 떼어내다, 제거하다 2. 성공하다..." 와
# 보기 "끌어서 떼어내다, 제거하다, 성공하다..." 를 동일하게 만든다.
_NON_MATCH = re.compile(r'[^가-힣a-zA-Z]')


def mnorm(text):
    text = unicodedata.normalize('NFKC', text or '')
    return _NON_MATCH.sub('', text)


def build_lookups():
    """data.json → 정규화된 양방향 맵.
    fwd[mnorm(front)] = back(raw),  bwd[mnorm(back)] = front(raw)."""
    try:
        json_path = os.path.join(os.getcwd(), 'data.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            cards = json.load(f)
    except FileNotFoundError:
        print("[테스트] 오류: data.json 파일을 찾을 수 없습니다.")
        return None, None
    except json.JSONDecodeError:
        print("[테스트] 오류: data.json 형식이 잘못되었습니다.")
        return None, None

    fwd, bwd = {}, {}
    for card in cards:
        front = card.get('front', '')
        back = card.get('back', '')
        if front:
            fwd[mnorm(front)] = back
        if back:
            bwd[mnorm(back)] = front
    print(f"[테스트] 매칭 데이터 로드 완료 (카드 {len(cards)}개)")
    return fwd, bwd


# 현재 보이는 문제(.flip-card.showing)만 읽는다.
#  - flipped: 'flip' 클래스 = 뒷면(6개 보기)이 활성화된 상태
#  - prompt:  .flip-card-front .front-hidden 의 텍스트 (정확한 문제 단어/뜻)
#  - options: .flip-card-back 의 보이는 라벨 (번호 = for 끝자리, 텍스트 = .cc-table)
#  - qid:     test_question[] 값 (문제 고유 ID, 전환 감지용)
_READ_QUESTION_JS = r'''
var card = document.querySelector('.flip-card.showing');
if (!card) return { found: false };

var qid = '';
var qi = card.querySelector('input[name="test_question[]"]');
if (qi) qid = qi.value;

var flipped = card.classList.contains('flip');

var prompt = '';
var fh = card.querySelector('.flip-card-front .front-hidden');
if (fh) prompt = (fh.textContent || '').trim();
if (!prompt) {
    var fb = card.querySelector('.flip-card-front .cc-table');
    if (fb) prompt = (fb.textContent || '').trim();
}

var options = [];
var seen = {};
var labels = card.querySelectorAll('.flip-card-back label[for^="radio_"]:not(.hidden)');
for (var i = 0; i < labels.length; i++) {
    var l = labels[i];
    var f = l.getAttribute('for') || '';
    var parts = f.split('_');
    var num = parseInt(parts[parts.length - 1], 10);
    if (!num || seen[num]) continue;
    seen[num] = true;
    var cc = l.querySelector('.cc-table');
    var t = ((cc ? cc.textContent : l.textContent) || '').trim();
    if (!t) continue;
    options.push({ num: num, text: t });
}

return { found: true, qid: qid, flipped: flipped, prompt: prompt, options: options };
'''


def read_question(driver):
    """returns dict: {found, qid, flipped, prompt_raw, options:[(num, raw, mnorm)]} 또는 None."""
    try:
        data = driver.execute_script(_READ_QUESTION_JS)
    except NoSuchWindowException:
        raise
    except Exception:
        return None
    if not data or not data.get('found'):
        return None

    options = []
    for o in data.get('options', []):
        num = o.get('num')
        raw = (o.get('text') or '').strip()
        if num and raw:
            options.append((num, raw, mnorm(raw)))

    return {
        'qid': data.get('qid') or '',
        'flipped': bool(data.get('flipped')),
        'prompt_raw': (data.get('prompt') or '').strip(),
        'options': options,
    }


def _ratio(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def solve(prompt_raw, options, fwd, bwd):
    """현재 보기에서 정답 번호를 찾는다. (prompt→정답→보기, 실패 시 보기→짝→prompt 역방향,
    그래도 실패 시 유사도 기반 폴백)
    returns (match_num, answer_raw) 또는 (None, None)."""
    pm = mnorm(prompt_raw)

    # 1) 프롬프트 → 정답 → 보기 (정확/부분)
    ans = fwd.get(pm) or bwd.get(pm)
    if ans:
        am = mnorm(ans)
        for num, _, om in options:
            if om == am:
                return num, ans
        for num, _, om in options:
            if am and (am in om or om in am):
                return num, ans

    # 2) 역방향: 각 보기의 짝을 구해 프롬프트와 비교 (정확/부분)
    for num, oraw, om in options:
        cp = fwd.get(om) or bwd.get(om)
        if cp and mnorm(cp) == pm:
            return num, oraw
    for num, oraw, om in options:
        cp = fwd.get(om) or bwd.get(om)
        if cp:
            cpm = mnorm(cp)
            if cpm and (cpm in pm or pm in cpm):
                return num, oraw

    # 3) 유사도 폴백: 정답 텍스트와 가장 비슷한 보기 (부가설명 차이 등 대비)
    if ans:
        am = mnorm(ans)
        best_num, best = None, 0.0
        for num, _, om in options:
            s = _ratio(am, om)
            if s > best:
                best, best_num = s, num
        if best_num is not None and best >= 0.6:
            return best_num, ans

    # 4) 유사도 폴백(역방향): 각 보기의 짝과 프롬프트 비교
    best_num, best, best_ans = None, 0.0, None
    for num, oraw, om in options:
        cp = fwd.get(om) or bwd.get(om)
        if not cp:
            continue
        s = _ratio(mnorm(cp), pm)
        if s > best:
            best, best_num, best_ans = s, num, oraw
    if best_num is not None and best >= 0.6:
        return best_num, best_ans

    return None, None


def _press_number(driver, n):
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(str(n))
        return True
    except NoSuchWindowException:
        raise
    except Exception:
        return False


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


def _click_when_ready(driver, selector, timeout=8):
    """selector 가 보이면 클릭. 못 찾으면 False (best-effort)."""
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        _click(driver, el)
        return True
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def _click_exit(driver, timeout=8):
    """'나가기' 버튼 클릭 (텍스트 우선, 없으면 set 링크 폴백)."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            links = driver.find_elements(By.CSS_SELECTOR, 'a')
            # 1) 텍스트가 '나가기'
            for a in links:
                try:
                    if a.is_displayed() and '나가기' in (a.text or ''):
                        _click(driver, a)
                        return True
                except Exception:
                    continue
            # 2) 폴백: set 상세로 가는 primary 링크
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
    """결과 화면(btn-go-result)이 보이면 제출결과확인 → X → 나가기 순으로 빠져나와
    set 상세 화면 복귀 후 stop_event.set()."""
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, GO_RESULT_SELECTOR)
        visible = [b for b in buttons if b.is_displayed()]
        if not visible:
            return False

        # 1) 제출 결과 확인
        _click(driver, visible[0])
        time.sleep(0.8)

        # 2) X 닫기
        _click_when_ready(driver, 'i.cc.times', timeout=8)
        time.sleep(0.8)

        # 3) 나가기 → set 상세 화면
        _click_exit(driver, timeout=8)
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


def _plan_wrong_indices(total):
    """TARGET_SCORE에 맞춰 일부러 틀릴 문항 순번(1-based) 집합.
    틀릴 개수 = round(total * (100 - TARGET_SCORE) / 100)."""
    if not total or total <= 0:
        return set()
    n_wrong = round(total * (100 - TARGET_SCORE) / 100.0)
    n_wrong = max(0, min(n_wrong, total))
    if n_wrong == 0:
        return set()
    return set(random.sample(range(1, total + 1), n_wrong))


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[테스트] 시작")

    suppress_leave_detection(driver)  # 백그라운드 실행 시 '이탈 감지' 우회

    fwd, bwd = build_lookups()
    if fwd is None:
        print("[테스트] 종료")
        return

    total = _count_total(driver)
    wrong_idx = _plan_wrong_indices(total)
    if DEBUG and total:
        print(f"[테스트] 총 {total}문항 / 일부러 틀릴 순번: {sorted(wrong_idx) or '없음'}")

    last_qid = None       # 이미 답한 문제 ID (전환 감지)
    spaced_qid = None     # SPACE로 flip 시도한 문제 ID (중복 방지)
    answered_count = 0    # 실제로 답한 수 (오답 주입 인덱스)
    last_dbg = None

    try:
        while not stop_event.is_set():
            if check_end_and_stop(driver, stop_event):
                break

            q = read_question(driver)
            if q is None or not q['options']:
                if stop_event.wait(timeout=0.3):
                    break
                continue

            qid = q['qid']
            flipped = q['flipped']
            prompt_raw = q['prompt_raw']
            options = q['options']

            match_num, answer = solve(prompt_raw, options, fwd, bwd)

            if DEBUG:
                dbg = (qid, flipped, prompt_raw, match_num)
                if dbg != last_dbg:
                    last_dbg = dbg
                    state = "보기" if flipped else "단어"
                    print(f"[감지] {state} | prompt={prompt_raw!r} | 정답번호={match_num} | qid={qid}")

            # 이미 답한 문제 → 다음 문제로 넘어갈 때까지 대기
            if qid and qid == last_qid:
                if stop_event.wait(timeout=0.3):
                    break
                continue

            # 단어 카드(아직 안 뒤집힘) → SPACE로 6개 보기로 넘김 (문제당 1회)
            if not flipped:
                if spaced_qid != qid:
                    _press_space(driver)
                    spaced_qid = qid
                if stop_event.wait(timeout=0.4):
                    break
                continue

            # 6개 보기 활성 → 답 선택
            answered_count += 1
            make_wrong = answered_count in wrong_idx
            all_nums = [num for num, _, _ in options]

            if match_num is not None and not make_wrong:
                choose = match_num
            else:
                wrong_nums = [x for x in all_nums if x != match_num]
                choose = random.choice(wrong_nums) if wrong_nums else (all_nums[0] if all_nums else 1)
                if make_wrong:
                    print(f"[테스트] {answered_count}번째: 의도적 오답 ({prompt_raw!r})")
                elif match_num is None:
                    print(f"[테스트] {answered_count}번째: 매칭 실패 → 랜덤 ({prompt_raw!r})")

            if DEBUG:
                print(f"[테스트][{answered_count}] {prompt_raw!r} → 정답='{answer}' → {choose}번 선택")

            # 활성 직후 너무 빨리 누르면 씹힘 → 0.5초 후 입력
            if stop_event.wait(timeout=0.5):
                break
            _press_number(driver, choose)
            last_qid = qid
            if stop_event.wait(timeout=0.5):
                break

    except NoSuchWindowException:
        pass
    except Exception as e:
        if not stop_event.is_set():
            print(f"[테스트] 오류: {e}")
    finally:
        print("[테스트] 종료")
