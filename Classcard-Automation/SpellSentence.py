import threading
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchWindowException

from MemorizeSentence import normalize_text, parse_english_words, click_scramble_word


# 문장 set의 스펠은 옵션 화면의 유형에 따라 학습 화면이 다르다. 카드마다 화면을 보고 판별한다.
#  - 어순배열: 한글 제시문(.para_item) + 단어 타일(.scramble-item)을 순서대로 클릭
#  - 영작:     한글 제시문(.back-body) + 입력창(textarea.input-answer)에 영어 문장을 타이핑 → '확인'
# 둘 다 정답이면 카드가 data-status='k'가 되고 'Good Job! / 다음 카드' 버튼이 뜨며, 자동으로 넘어가지
# 않으므로 직접 눌러야 한다. 완료율은 마지막 카드에서 '다음 카드'를 눌러 종료 화면(#study_end)까지
# 가야 서버에 기록되므로, 카운터가 다 차도 조기 종료하지 않고 종료 화면에서 '학습종료'로 나간다
# (SPACE는 절대 안 씀 → 200% 방지).
NEXT_BTN_TEXTS = ('다음 카드',)
CONFIRM_BTN_TEXTS = ('확인',)
EXIT_BTN_TEXTS = ('학습종료', '학습 종료')  # 종료 화면은 '학습종료', 옵션 화면은 '학습 종료'
INPUT_SELECTOR = '.CardItem.active textarea.input-answer'
MAX_STUCK = 4  # 같은 카드에서 이 횟수만큼 진행이 안 되면 중단 (무한루프 방지)

_READ_CARD_JS = r'''
var c = document.querySelector('.CardItem.active');
if (!c || c.offsetParent === null) return null;
var done = c.getAttribute('data-status') === 'k';
var tiles = c.querySelectorAll('.scramble-item');
if (tiles.length) {
    var items = c.querySelectorAll('span.para_item'), parts = [];
    for (var i = 0; i < items.length; i++) {
        var t = (items[i].textContent || '').trim();
        if (t) parts.push(t);
    }
    if (!done) done = c.querySelectorAll('.scramble-item:not(.clicked)').length === 0;
    return {kind: 'scramble', korean: parts.join(' '), done: done};
}
var ta = c.querySelector('textarea.input-answer');
if (ta) {
    var body = c.querySelector('.back-body'), kor = '';
    if (body) {
        var divs = body.children;
        for (var j = divs.length - 1; j >= 0; j--) {
            if (divs[j].classList.contains('icon')) continue;
            kor = (divs[j].textContent || '').trim();
            if (kor) break;
        }
    }
    return {kind: 'write', korean: kor, done: done};
}
return {kind: null, korean: '', done: done};
'''


def prepare_options(driver):
    """시작 전 옵션 화면에서 호출. 유형이 '딕테이션'(듣고 받아쓰기, 한글 제시문이 없어 자동화 불가)이면
    '어순배열'로 바꾼다. 어순배열/영작은 그대로 둔다."""
    try:
        changed = driver.execute_script(r'''
            var cur = document.querySelector('input.study_type:checked');
            if (!cur || cur.value !== '2') return false;
            var r = document.querySelector('input.study_type[value="1"]');
            if (!r || r.disabled) return false;
            (r.closest('label') || r).click();
            return r.checked;
        ''')
        if changed:
            print("[문장 스펠] 유형이 딕테이션이라 어순배열로 바꿉니다.")
    except NoSuchWindowException:
        raise
    except Exception:
        pass


def read_card(driver):
    """현재 카드의 {kind: 'scramble'|'write'|None, korean, done}. 카드가 없으면 None."""
    try:
        return driver.execute_script(_READ_CARD_JS)
    except NoSuchWindowException:
        raise
    except Exception:
        return None


def _click_visible_text(driver, texts) -> bool:
    """보이는 a/button 중 텍스트가 texts 중 하나와 정확히 같은 첫 요소를 클릭."""
    try:
        return bool(driver.execute_script(r'''
            var els = document.querySelectorAll('a, button');
            for (var i = 0; i < els.length; i++) {
                var e = els[i];
                if (e.offsetParent === null) continue;
                var t = (e.textContent || '').trim();
                for (var j = 0; j < arguments[0].length; j++) {
                    if (t === arguments[0][j]) { e.click(); return true; }
                }
            }
            return false;
        ''', list(texts)))
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def end_screen_visible(driver) -> bool:
    try:
        return bool(driver.execute_script(r'''
            if (document.querySelector('#study_end.active')) return true;
            var b = document.querySelectorAll('.btn-study-end-repeat');
            for (var i = 0; i < b.length; i++) if (b[i].offsetParent !== null) return true;
            return false;
        '''))
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def exit_to_set(driver, stop_event):
    """종료 화면(또는 학습 화면)에서 셋홈으로 복귀: '학습 종료' 클릭.
    없으면 '학습 중지'(.btn-back) → 옵션 화면의 '학습 종료'."""
    for _ in range(3):
        if _click_visible_text(driver, EXIT_BTN_TEXTS):
            break
        try:
            driver.execute_script("var b = document.querySelector('.btn-back'); if (b) b.click();")
        except Exception:
            pass
        if stop_event.wait(timeout=0.8):
            break
    stop_event.set()


def find_english(answer_dict, korean):
    if not korean or not answer_dict:
        return None
    nk = normalize_text(korean)
    for k, v in answer_dict.items():
        if nk == normalize_text(k):
            return v
    return None


def card_done(driver) -> bool:
    card = read_card(driver)
    return bool(card and card.get('done'))


def _korean_now(driver):
    card = read_card(driver)
    return card.get('korean') if card else None


def click_next_card(driver) -> bool:
    """보이는 '다음 카드' 버튼 클릭. 없으면 False."""
    return _click_visible_text(driver, NEXT_BTN_TEXTS)


def _answer_scramble(driver, english, stop_event):
    """어순배열: 영어 문장의 단어 타일을 순서대로 클릭."""
    for word in parse_english_words(english):
        if stop_event.is_set():
            return
        # 타일이 늦게 나타날 수 있어 재시도
        for _ in range(10):
            if click_scramble_word(driver, word):
                break
            if stop_event.wait(timeout=0.2):
                return
        if stop_event.wait(timeout=0.15):
            return


def _answer_write(driver, english, stop_event) -> bool:
    """영작: 입력창에 영어 문장을 타이핑하고 '확인'. (붙여넣기가 막혀 있어 키 입력으로 넣는다)"""
    try:
        box = driver.find_element(By.CSS_SELECTOR, INPUT_SELECTOR)
    except NoSuchWindowException:
        raise
    except Exception:
        return False
    try:
        try:
            box.click()
        except Exception:
            driver.execute_script("arguments[0].focus();", box)
        box.clear()
        box.send_keys(english)
    except NoSuchWindowException:
        raise
    except Exception as e:
        print(f"[문장 스펠] 입력 오류: {e}")
        return False
    if stop_event.wait(timeout=0.2):
        return False
    return _click_visible_text(driver, CONFIRM_BTN_TEXTS)


def _wait(driver, stop_event, total, cond, interval=0.2):
    """total초 동안 cond()가 참이 되거나 종료 화면/중지될 때까지 대기.
    반환: 'ok' | 'done' | 'stopped' | 'timeout'"""
    waited = 0.0
    while waited < total:
        if stop_event.wait(timeout=interval):
            return 'stopped'
        waited += interval
        if end_screen_visible(driver):
            exit_to_set(driver, stop_event)
            return 'done'
        if cond():
            return 'ok'
    return 'timeout'


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[문장 스펠] 시작")
    if not answer_dict:
        print("[문장 스펠] answer_dict가 없습니다. 종료")
        return

    last_korean = None
    stuck = 0       # 같은 카드에서 진행이 안 된 횟수
    idle = 0        # 카드/유형을 못 읽은 연속 횟수
    announced = None

    try:
        while not stop_event.is_set():
            if end_screen_visible(driver):
                exit_to_set(driver, stop_event)
                break

            card = read_card(driver)
            korean = card.get('korean') if card else None
            kind = card.get('kind') if card else None
            if not korean or not kind:
                idle += 1
                if idle > 40:
                    print("[문장 스펠] 지원하지 않는 화면입니다 (어순배열/영작만 지원). 종료")
                    exit_to_set(driver, stop_event)
                    break
                if stop_event.wait(timeout=0.4):
                    break
                continue
            idle = 0

            if kind != announced:
                announced = kind
                print(f"[문장 스펠] 유형: {'어순배열' if kind == 'scramble' else '영작'}")

            # 같은 카드가 계속되면 진행이 막힌 것 → 무한루프 방지
            if korean == last_korean:
                stuck += 1
                if stuck >= MAX_STUCK:
                    print(f"[문장 스펠] 진행이 막혀 종료합니다: {korean!r}")
                    exit_to_set(driver, stop_event)
                    break
            else:
                last_korean, stuck = korean, 0

            # 이미 정답 처리된 카드면 다음 카드로
            if card.get('done'):
                click_next_card(driver)
                if _wait(driver, stop_event, 3.0, lambda: _korean_now(driver) != korean) in ('done', 'stopped'):
                    break
                continue

            english = find_english(answer_dict, korean)
            if not english:
                print(f"[문장 스펠] 매칭 실패: {korean!r}")
                if stop_event.wait(timeout=1.0):
                    break
                continue

            if kind == 'scramble':
                _answer_scramble(driver, english, stop_event)
            else:
                _answer_write(driver, english, stop_event)
            if stop_event.is_set():
                break

            # 정답 판정 대기 → '다음 카드' → 제시문이 바뀔 때까지 대기
            status = _wait(driver, stop_event, 3.0, lambda: card_done(driver))
            if status in ('done', 'stopped'):
                break
            if status == 'timeout':
                print(f"[문장 스펠] 정답 처리 안 됨: {korean!r}")
                continue
            click_next_card(driver)
            if _wait(driver, stop_event, 3.0, lambda: _korean_now(driver) != korean) in ('done', 'stopped'):
                break

    except NoSuchWindowException:
        pass
    except Exception as e:
        if not stop_event.is_set():
            print(f"[문장 스펠] 오류: {e}")
    finally:
        print("[문장 스펠] 종료")
