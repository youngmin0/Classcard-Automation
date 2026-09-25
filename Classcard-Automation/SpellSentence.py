import threading
from selenium.common.exceptions import NoSuchWindowException

from MemorizeSentence import (
    normalize_text, get_korean_sentence, parse_english_words, click_scramble_word,
)


# 문장 set의 스펠은 입력창이 아니라 단어 타일 배열(스크램블) UI다.
# 한글 제시문(.para_item) → answer_dict(한글→영어)로 정답 문장을 찾아 타일을 순서대로 클릭.
# 완성되면 'Good Job! / 다음 카드' 버튼이 뜨고 자동으로 넘어가지 않으므로 직접 눌러야 한다.
# 완료율은 마지막 카드에서 '다음 카드'를 눌러 종료 화면(#study_end)까지 가야 서버에 기록되므로,
# 카운터가 다 차도 조기 종료하지 않고 종료 화면에서 '학습 종료'로 나간다 (SPACE는 절대 안 씀 → 200% 방지).
NEXT_BTN_TEXTS = ('다음 카드',)
EXIT_BTN_TEXTS = ('학습종료', '학습 종료')  # 종료 화면은 '학습종료', 옵션 화면은 '학습 종료'


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
    """현재 카드가 완성 판정(data-status='k')됐거나 남은 타일이 없으면 True."""
    try:
        return bool(driver.execute_script(r'''
            var c = document.querySelector('.CardItem.scramble.active');
            if (!c) return false;
            if (c.getAttribute('data-status') === 'k') return true;
            return c.querySelectorAll('.scramble-item:not(.clicked)').length === 0;
        '''))
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def click_next_card(driver) -> bool:
    """보이는 '다음 카드' 버튼 클릭. 없으면 False."""
    return _click_visible_text(driver, NEXT_BTN_TEXTS)


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

    try:
        while not stop_event.is_set():
            if end_screen_visible(driver):
                exit_to_set(driver, stop_event)
                break

            korean = get_korean_sentence(driver)
            if not korean:
                if stop_event.wait(timeout=0.4):
                    break
                continue

            # 이미 완성된 카드(이전 루프에서 배치 완료)면 다음 카드로
            if card_done(driver):
                click_next_card(driver)
                if _wait(driver, stop_event, 3.0, lambda: get_korean_sentence(driver) != korean) in ('done', 'stopped'):
                    break
                continue

            english = find_english(answer_dict, korean)
            if not english:
                print(f"[문장 스펠] 매칭 실패(건너뜀): {korean!r}")
                click_next_card(driver)
                if stop_event.wait(timeout=1.0):
                    break
                continue

            for word in parse_english_words(english):
                if stop_event.is_set():
                    break
                # 타일이 늦게 나타날 수 있어 재시도
                for _ in range(10):
                    if click_scramble_word(driver, word):
                        break
                    if stop_event.wait(timeout=0.2):
                        break
                if stop_event.wait(timeout=0.15):
                    break
            if stop_event.is_set():
                break

            # 완성 판정 대기 → '다음 카드' → 제시문이 바뀔 때까지 대기
            status = _wait(driver, stop_event, 3.0, lambda: card_done(driver))
            if status in ('done', 'stopped'):
                break
            if status == 'timeout':
                print(f"[문장 스펠] 완성 안 됨(건너뜀): {korean!r}")
            click_next_card(driver)
            if _wait(driver, stop_event, 3.0, lambda: get_korean_sentence(driver) != korean) in ('done', 'stopped'):
                break

    except NoSuchWindowException:
        pass
    except Exception as e:
        if not stop_event.is_set():
            print(f"[문장 스펠] 오류: {e}")
    finally:
        print("[문장 스펠] 종료")
