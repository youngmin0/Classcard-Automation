import os
import re
import html
import json
import time
import random
import threading
import unicodedata
from selenium.common.exceptions import NoSuchWindowException


# 진단용: True면 스크램블 과정을 터미널에 출력
DEBUG = False

# 필수 학습(4000점)을 채우되 끝까지 가지 않도록, 이 범위 안에서 목표 점수를 정해
# 도달하면 게임 도중에 빠져나간다 (점수는 저장됨).
EXIT_SCORE_MIN = 4000
EXIT_SCORE_MAX = 5000

# 스크램블(문장 매칭) 보드 셀렉터
PROMPT_SELECTOR = '.quest-back'                       # 한국어 문제 문장
PLACED_SELECTOR = '.user-input-body .user-box'        # 지금까지 배치한 단어 (? = 빈칸)
WORD_SELECTOR = '.suggest-body .word-box'             # 클릭할 후보 단어 타일
SCORE_SELECTOR = '.txt-total-score'                   # 현재 점수


# 스크램블 '이탈 감지' 우회: 탭/창 포커스를 잃어도 보이는/포커스된 상태로 위장 (백그라운드 실행).
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
    try:
        driver.execute_script(_ANTI_BLUR_JS)
    except NoSuchWindowException:
        raise
    except Exception:
        pass


_TAG = re.compile(r'<[^>]+>')
# 한국어 문제 정규화: 한글/영문 글자만 남김 (숫자/공백/구두점 제거)
_NON_KO = re.compile(r'[^가-힣a-zA-Z]')
# 영단어 정규화: 영숫자만 (대소문자/구두점 제거)
_NON_WORD = re.compile(r'[^a-zA-Z0-9]')


def _strip_tags(text):
    text = _TAG.sub(' ', text or '')
    return html.unescape(text)


def knorm(text):
    """한국어 문제 문장 정규화."""
    text = unicodedata.normalize('NFKC', _strip_tags(text))
    return _NON_KO.sub('', text)


def wnorm(word):
    """영단어 정규화 (구두점/대소문자 무시)."""
    word = unicodedata.normalize('NFKC', word or '')
    return _NON_WORD.sub('', word).lower()


def _strip_edge_punct(word):
    """양 끝 구두점만 제거 (대소문자/내부 어포스트로피 유지)."""
    return re.sub(r'^[^\w]+|[^\w]+$', '', word or '')


def _load_cards(driver):
    """현재 스크램블 페이지의 전역 study_data(front=영어 문장/back=한국어) 우선.
    실패 시 디스크 data.json 폴백."""
    if driver is not None:
        try:
            cards = driver.execute_script(
                "return (typeof study_data !== 'undefined') ? study_data : null;"
            )
            if cards:
                print(f"[스크램블] 페이지 study_data 로드 (카드 {len(cards)}개)")
                return cards
        except NoSuchWindowException:
            raise
        except Exception:
            pass

    try:
        json_path = os.path.join(os.getcwd(), 'data.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            cards = json.load(f)
        print(f"[스크램블] data.json 폴백 로드 (카드 {len(cards)}개)")
        return cards
    except FileNotFoundError:
        print("[스크램블] 오류: study_data도 없고 data.json도 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        print("[스크램블] 오류: data.json 형식이 잘못되었습니다.")
        return None


def build_lookup(driver=None):
    """knorm(back 한국어) → front(영어 문장) 맵."""
    cards = _load_cards(driver)
    if cards is None:
        return None
    lookup = {}
    for card in cards:
        front = card.get('front', '')
        back = card.get('back', '')
        if front and back:
            lookup[knorm(back)] = _strip_tags(front).strip()
    return lookup


_READ_STATE_JS = r'''
var qb = document.querySelector(arguments[0]);
var prompt = qb ? (qb.textContent || '').trim() : '';

var placed = [];
var ub = document.querySelectorAll(arguments[1]);
for (var i = 0; i < ub.length; i++) {
    var t = (ub[i].textContent || '').trim();
    if (t && t !== '?') placed.push(t);
}

var cands = [];
var wb = document.querySelectorAll(arguments[2]);
for (var i = 0; i < wb.length; i++) {
    cands.push((wb[i].textContent || '').trim());
}

return { prompt: prompt, placed: placed, cands: cands };
'''


def read_state(driver):
    """returns {'prompt','placed':[...],'cands':[...]} 또는 None."""
    try:
        data = driver.execute_script(
            _READ_STATE_JS, PROMPT_SELECTOR, PLACED_SELECTOR, WORD_SELECTOR
        )
    except NoSuchWindowException:
        raise
    except Exception:
        return None
    return data


def find_next_index(target_words, placed, cands):
    """다음에 클릭할 후보 인덱스를 찾는다.
    returns (idx, need): idx=클릭할 word-box 인덱스, need=정답 단어.
      - (None, None): 문장 완성 (다음 문제 대기)
      - (None, need): 다음 단어를 후보에서 아직 못 찾음 (잠시 후 재시도)"""
    i = len(placed)
    if i >= len(target_words):
        return None, None

    need = target_words[i]

    # 1) 정확 일치
    for idx, c in enumerate(cands):
        if c == need:
            return idx, need
    # 2) 양 끝 구두점만 제거 (대소문자 유지)
    ns = _strip_edge_punct(need)
    if ns:
        for idx, c in enumerate(cands):
            if _strip_edge_punct(c) == ns:
                return idx, need
    # 3) 완전 정규화 (구두점/대소문자 무시)
    nn = wnorm(need)
    if nn:
        for idx, c in enumerate(cands):
            if wnorm(c) == nn:
                return idx, need

    return None, need


def click_word(driver, index):
    try:
        driver.execute_script(
            "var e = document.querySelectorAll(arguments[0]); "
            "if (e[arguments[1]]) e[arguments[1]].click();",
            WORD_SELECTOR, index,
        )
        return True
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def read_score(driver):
    """현재 점수(.txt-total-score)를 정수로 반환. 못 읽으면 None."""
    try:
        return driver.execute_script(r'''
            var els = document.querySelectorAll(arguments[0]);
            for (var i = 0; i < els.length; i++) {
                var n = parseInt((els[i].textContent || '').replace(/[^0-9]/g, ''), 10);
                if (!isNaN(n)) return n;
            }
            return null;
        ''', SCORE_SELECTOR)
    except NoSuchWindowException:
        raise
    except Exception:
        return None


def _is_set_home(driver):
    """set 상세(셋홈) 페이지인지: .btn-summary 가 있으면 True."""
    try:
        return bool(driver.execute_script(
            "return document.querySelectorAll('.btn-summary').length > 0;"
        ))
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def _return_to_set_home(driver, stop_event, timeout=10):
    """게임/점수 화면에서 '학습 종료'(history.back)로 set 상세(셋홈) 복귀.
    스크램블은 상단 뒤로가기가 곧바로 history.back()이라 별도 확인 모달이 없다."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if stop_event.is_set() or _is_set_home(driver):
            return True
        clicked = driver.execute_script(r'''
            function txt(el){ return (el.textContent || '').trim(); }
            // 1) '학습 종료' 텍스트 링크
            var as = document.querySelectorAll(
                '.start-opt-body a, .end-opt-body a, a[onclick*="history.back"]');
            for (var i = 0; i < as.length; i++) {
                if (/학습\s*종료/.test(txt(as[i]))) { as[i].click(); return true; }
            }
            // 2) '종료'(btn-rank-cancel)
            var c = document.querySelector('.btn-rank-cancel');
            if (c) { c.click(); return true; }
            return false;
        ''')
        if not clicked:
            try:
                driver.execute_script("history.back();")
            except Exception:
                pass
        time.sleep(0.5)
    return _is_set_home(driver)


def check_end_and_stop(driver, stop_event):
    """게임 종료 화면(점수/랭킹판 .start-opt-body·.end-opt-body)이 보이면
    '학습 종료'로 set 상세(셋홈) 복귀 후 stop_event.set()."""
    try:
        ended = driver.execute_script(r'''
            function vis(el){ return el && el.offsetParent !== null; }
            return vis(document.querySelector('.start-opt-body'))
                || vis(document.querySelector('.end-opt-body'));
        ''')
        if not ended:
            return False
        _return_to_set_home(driver, stop_event)
        stop_event.set()
        return True
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[스크램블] 시작")

    suppress_leave_detection(driver)  # 백그라운드 실행 시 '이탈 감지' 우회

    lookup = build_lookup(driver)
    if lookup is None:
        print("[스크램블] 종료")
        return

    target_score = random.randint(EXIT_SCORE_MIN, EXIT_SCORE_MAX)
    print(f"[스크램블] 목표 점수 {target_score} 도달 시 종료")

    nomatch_streak = 0  # 다음 단어를 못 찾은 연속 횟수

    try:
        while not stop_event.is_set():
            if check_end_and_stop(driver, stop_event):
                break

            # 목표 점수 도달 시 셋홈으로 빠져나감 (점수는 저장됨)
            score = read_score(driver)
            if score is not None and score >= target_score:
                print(f"[스크램블] 목표 점수 도달 (현재 {score}) → 종료")
                _return_to_set_home(driver, stop_event)
                stop_event.set()
                break

            state = read_state(driver)
            if not state or not state.get('prompt'):
                if stop_event.wait(timeout=0.3):
                    break
                continue

            prompt = state['prompt']
            placed = state.get('placed', [])
            cands = state.get('cands', [])

            target = lookup.get(knorm(prompt))
            if not target:
                if DEBUG:
                    print(f"[스크램블] 문제 매칭 실패: {prompt!r}")
                if stop_event.wait(timeout=0.4):
                    break
                continue

            target_words = target.split()
            idx, need = find_next_index(target_words, placed, cands)

            if idx is None and need is None:
                # 문장 완성 → 다음 문제 대기
                if stop_event.wait(timeout=0.3):
                    break
                continue

            if idx is None:
                # 다음 단어가 아직 후보에 없음 (애니메이션/로딩) → 잠시 후 재시도
                nomatch_streak += 1
                if DEBUG:
                    print(f"[스크램블] 다음 단어 '{need}' 후보에 없음 (cands={cands})")
                if nomatch_streak >= 10:
                    if check_end_and_stop(driver, stop_event):
                        break
                if stop_event.wait(timeout=0.3):
                    break
                continue
            nomatch_streak = 0

            if DEBUG:
                print(f"[스크램블] {len(placed)+1}/{len(target_words)} → '{need}' (idx {idx})")

            click_word(driver, idx)
            if stop_event.wait(timeout=0.25):
                break

    except NoSuchWindowException:
        pass
    except Exception as e:
        if not stop_event.is_set():
            print(f"[스크램블] 오류: {e}")
    finally:
        print("[스크램블] 종료")
