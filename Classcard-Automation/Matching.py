import os
import re
import html
import json
import time
import random
import difflib
import threading
import unicodedata
from selenium.common.exceptions import NoSuchWindowException


# 진단용: True면 매칭 과정을 터미널에 출력
DEBUG = False

# 필수 학습(1000점)을 채우되 끝까지 가지 않도록, 이 범위 안에서 목표 점수를 정해
# 도달하면 게임 도중에 '매칭종료'로 빠져나간다 (점수는 저장됨).
EXIT_SCORE_MIN = 1000
EXIT_SCORE_MAX = 2000

# 매칭 보드 셀렉터
LEFT_CARD_SELECTOR = '.match-body.left .flip-card'    # 영어
RIGHT_CARD_SELECTOR = '.match-body.right .flip-card'  # 한국어
MATCH_TEXT_SELECTOR = '.match-text > div[style*="font-size"]'


# 매칭 '이탈 감지' 우회: 탭/창 포커스를 잃어도 보이는/포커스된 상태로 위장 (백그라운드 실행).
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


# 매칭용 정규화: 한글/영문 글자만 남김 (숫자/공백/구두점 제거).
# 프롬프트 "1. 켜다 2. 자극하다, 흥분시키다" 와 보기 텍스트를 동일하게 만든다.
_NON_MATCH = re.compile(r'[^가-힣a-zA-Z]')
_TAG = re.compile(r'<[^>]+>')


def _strip_tags(text):
    """card_list 값의 <br> 등 HTML 태그/엔티티 제거 (DOM 표시 텍스트와 맞추기 위함)."""
    text = _TAG.sub(' ', text or '')
    return html.unescape(text)


def mnorm(text):
    text = unicodedata.normalize('NFKC', _strip_tags(text))
    return _NON_MATCH.sub('', text)


def _load_cards(driver):
    """현재 매칭 페이지의 전역 card_list(front=영어/back=한국어)를 우선 사용.
    실패 시 디스크 data.json 폴백."""
    if driver is not None:
        try:
            cards = driver.execute_script(
                "return (typeof card_list !== 'undefined') ? card_list : null;"
            )
            if cards:
                print(f"[매칭] 페이지 card_list 로드 (카드 {len(cards)}개)")
                return cards
        except NoSuchWindowException:
            raise
        except Exception:
            pass

    try:
        json_path = os.path.join(os.getcwd(), 'data.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            cards = json.load(f)
        print(f"[매칭] data.json 폴백 로드 (카드 {len(cards)}개)")
        return cards
    except FileNotFoundError:
        print("[매칭] 오류: card_list도 없고 data.json도 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        print("[매칭] 오류: data.json 형식이 잘못되었습니다.")
        return None


def build_lookups(driver=None):
    """정규화된 양방향 맵 생성.
    fwd[mnorm(front)] = back(raw),  bwd[mnorm(back)] = front(raw)."""
    cards = _load_cards(driver)
    if cards is None:
        return None, None

    fwd, bwd = {}, {}
    for card in cards:
        front = card.get('front', '')
        back = card.get('back', '')
        if front:
            fwd[mnorm(front)] = back
        if back:
            bwd[mnorm(back)] = front
    return fwd, bwd


# 현재 보드의 좌(영어)/우(한국어) 카드를 인덱스 순서대로 읽는다.
_READ_BOARD_JS = r'''
function read(sel) {
  var out = [];
  var cards = document.querySelectorAll(sel);
  for (var i = 0; i < cards.length; i++) {
    var c = cards[i];
    var t = c.querySelector('.match-text > div[style*="font-size"]');
    out.push((t ? t.textContent : '').trim());
  }
  return out;
}
return { left: read(arguments[0]), right: read(arguments[1]) };
'''


def read_board(driver):
    """returns {'left': [(idx, raw, norm)...], 'right': [...]} 또는 None."""
    try:
        data = driver.execute_script(_READ_BOARD_JS, LEFT_CARD_SELECTOR, RIGHT_CARD_SELECTOR)
    except NoSuchWindowException:
        raise
    except Exception:
        return None
    if not data:
        return None

    def conv(items):
        res = []
        for i, raw in enumerate(items or []):
            raw = (raw or '').strip()
            res.append((i, raw, mnorm(raw)))
        return res

    return {'left': conv(data.get('left')), 'right': conv(data.get('right'))}


def _ratio(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def find_pair(lefts, rights, fwd, bwd):
    """좌(영어)/우(한국어)에서 확실한 한 쌍을 찾아 (left_idx, right_idx, left_raw, right_raw) 반환.
    못 찾으면 (None, None, None, None)."""
    # 1) 정확 매칭: 영어 → 정답 한국어 → 보기 (정확/부분)
    for li, lraw, lnorm in lefts:
        if not lnorm:
            continue
        kr = fwd.get(lnorm) or bwd.get(lnorm)
        if not kr:
            continue
        krn = mnorm(kr)
        for ri, rraw, rnorm in rights:
            if rnorm and rnorm == krn:
                return li, ri, lraw, rraw
        for ri, rraw, rnorm in rights:
            if krn and rnorm and (krn in rnorm or rnorm in krn):
                return li, ri, lraw, rraw

    # 2) 유사도 폴백: 부가설명/구두점 차이 대비
    best = None  # (score, li, ri, lraw, rraw)
    for li, lraw, lnorm in lefts:
        if not lnorm:
            continue
        kr = fwd.get(lnorm) or bwd.get(lnorm)
        if not kr:
            continue
        krn = mnorm(kr)
        for ri, rraw, rnorm in rights:
            s = _ratio(krn, rnorm)
            if best is None or s > best[0]:
                best = (s, li, ri, lraw, rraw)
    if best and best[0] >= 0.6:
        return best[1], best[2], best[3], best[4]

    return None, None, None, None


def _click_card(driver, selector, index):
    """selector 에 매칭되는 index번째 카드를 클릭 (클릭 시점에 재조회)."""
    try:
        driver.execute_script(
            "var e = document.querySelectorAll(arguments[0]); "
            "if (e[arguments[1]]) e[arguments[1]].click();",
            selector, index,
        )
        return True
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def _wait_board_change(driver, stop_event, prev_left, timeout=2.5):
    """좌측 카드 텍스트 집합이 바뀔 때까지 대기 (매칭 성공 → 카드 교체 감지)."""
    prev = set(t for _, t, _ in prev_left)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if stop_event.wait(timeout=0.2):
            return True
        board = read_board(driver)
        if board is None:
            continue
        cur = set(t for _, t, _ in board['left'])
        if cur != prev:
            return False
    return False


def read_score(driver):
    """현재 매칭 점수(.match-top .point)를 정수로 반환. 못 읽으면 None."""
    try:
        return driver.execute_script(r'''
            var els = document.querySelectorAll('.match-top .point');
            for (var i = 0; i < els.length; i++) {
                if (els[i].offsetParent !== null) {
                    var n = parseInt((els[i].textContent || '').replace(/[^0-9]/g, ''), 10);
                    if (!isNaN(n)) return n;
                }
            }
            var e = document.querySelector('.match-top .point');
            if (e) {
                var n = parseInt((e.textContent || '').replace(/[^0-9]/g, ''), 10);
                if (!isNaN(n)) return n;
            }
            return null;
        ''')
    except NoSuchWindowException:
        raise
    except Exception:
        return None


def _is_set_home(driver):
    """set 상세(셋홈) 페이지인지: 매칭/암기 등 .btn-summary 가 있으면 True."""
    try:
        return bool(driver.execute_script(
            "return document.querySelectorAll('.btn-summary').length > 0;"
        ))
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def _return_to_set_home(driver, stop_event, timeout=8):
    """게임 종료 후 점수/랭킹 화면에서 '학습 종료'(history.back)로 set 상세(셋홈) 복귀."""
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
            # 폴백: 직접 뒤로가기
            try:
                driver.execute_script("history.back();")
            except Exception:
                pass
        time.sleep(0.5)
    return _is_set_home(driver)


def exit_mid_game(driver, stop_event):
    """게임 도중 상단 뒤로가기 → 확인 모달 '매칭종료'(.btn-ok) → 점수 화면 '학습 종료'
    까지 눌러 set 상세(셋홈) 복귀 후 stop_event.set(). (점수는 서버에 저장됨)"""
    try:
        driver.execute_script(r'''
            var b = document.querySelector('.study-header .btn-back');
            if (b) b.click(); else history.back();
        ''')

        # 확인 모달은 position:fixed (offsetParent=null)이므로 .in/display로 판정
        deadline = time.time() + 5
        while time.time() < deadline:
            if stop_event.is_set():
                break
            clicked = driver.execute_script(r'''
                var m = document.querySelector('#confirmModal');
                if (!m) return false;
                var shown = m.classList.contains('in')
                    || getComputedStyle(m).display !== 'none';
                if (!shown) return false;
                var b = m.querySelector('.btn-ok');
                if (b) { b.click(); return true; }
                return false;
            ''')
            if clicked:
                break
            time.sleep(0.2)

        time.sleep(0.8)
        # 점수/랭킹 화면 → '학습 종료'로 셋홈 복귀
        _return_to_set_home(driver, stop_event)
    except NoSuchWindowException:
        raise
    except Exception:
        pass
    finally:
        stop_event.set()
    return True


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
    print("[매칭] 시작")

    suppress_leave_detection(driver)  # 백그라운드 실행 시 '이탈 감지' 우회

    fwd, bwd = build_lookups(driver)
    if fwd is None:
        print("[매칭] 종료")
        return

    target_score = random.randint(EXIT_SCORE_MIN, EXIT_SCORE_MAX)
    print(f"[매칭] 목표 점수 {target_score} 도달 시 중도 종료")

    empty_streak = 0   # 보드가 비어있는 연속 횟수 (게임 종료 추정)
    nomatch_streak = 0  # 매칭 쌍을 못 찾은 연속 횟수

    try:
        while not stop_event.is_set():
            if check_end_and_stop(driver, stop_event):
                break

            # 목표 점수 도달 시 게임 도중 '매칭종료'로 빠져나감 (점수는 저장됨)
            score = read_score(driver)
            if score is not None and score >= target_score:
                print(f"[매칭] 목표 점수 도달 (현재 {score}) → 중도 종료")
                exit_mid_game(driver, stop_event)
                break

            board = read_board(driver)
            if board is None:
                if stop_event.wait(timeout=0.3):
                    break
                continue

            lefts = board['left']
            rights = board['right']

            # 보드가 비었으면 게임 종료(결과 화면 대기) 가능성
            if not lefts and not rights:
                empty_streak += 1
                if empty_streak >= 5:
                    if check_end_and_stop(driver, stop_event):
                        break
                if stop_event.wait(timeout=0.3):
                    break
                continue
            empty_streak = 0

            li, ri, lraw, rraw = find_pair(lefts, rights, fwd, bwd)

            if li is None:
                nomatch_streak += 1
                if DEBUG:
                    print(f"[매칭] 쌍 못 찾음 (left={[t for _, t, _ in lefts]})")
                # 카드 교체 타이밍과 겹쳤을 수 있으니 잠시 후 재시도
                if nomatch_streak >= 8:
                    if check_end_and_stop(driver, stop_event):
                        break
                if stop_event.wait(timeout=0.4):
                    break
                continue
            nomatch_streak = 0

            if DEBUG:
                print(f"[매칭] {lraw!r} ↔ {rraw!r} (L{li}/R{ri})")

            # 한국어(우) 먼저, 영어(좌) 나중 클릭
            _click_card(driver, RIGHT_CARD_SELECTOR, ri)
            if stop_event.wait(timeout=0.15):
                break
            _click_card(driver, LEFT_CARD_SELECTOR, li)

            # 매칭 성공 → 카드 교체될 때까지 대기
            if _wait_board_change(driver, stop_event, lefts, timeout=2.5):
                break

    except NoSuchWindowException:
        pass
    except Exception as e:
        if not stop_event.is_set():
            print(f"[매칭] 오류: {e}")
    finally:
        print("[매칭] 종료")
