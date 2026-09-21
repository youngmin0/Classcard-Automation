import time
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchWindowException

from StudyEnd import check_step2_success_and_stop, reset_progress


def _wait_with_check(driver, stop_event, total, interval=0.2):
    """total 초 동안 interval 간격으로 종료 체크하며 대기. 종료 발견 시 True."""
    elapsed = 0.0
    while elapsed < total:
        if stop_event.wait(timeout=min(interval, total - elapsed)):
            return True
        elapsed += interval
        if check_step2_success_and_stop(driver, stop_event):
            return True
    return False


def get_card_key(driver):
    """현재 보이는 카드의 식별자(전환 감지용). data-idx만 사용한다.
    (flip 등으로 텍스트가 바뀌어도 같은 카드면 동일해야 하므로 textContent 폴백 금지.)
    못 읽으면 None → 타이머 방식 폴백."""
    try:
        return driver.execute_script(r'''
            var c = document.querySelector('.CardItem.current')
                 || document.querySelector('.CardItem.active')
                 || document.querySelector('.showing');
            if (!c) return null;
            return c.getAttribute('data-idx') || c.getAttribute('data-card-idx') || null;
        ''')
    except NoSuchWindowException:
        raise
    except Exception:
        return None


def _wait_change_or_stop(driver, stop_event, prev_key, total, interval=0.2):
    """total초 동안 카드 전환/완료/중지를 감지. 감지 시 True (재시도 종료)."""
    elapsed = 0.0
    while elapsed < total:
        if stop_event.wait(timeout=min(interval, total - elapsed)):
            return True
        elapsed += interval
        if check_step2_success_and_stop(driver, stop_event):
            return True
        cur = get_card_key(driver)
        if cur is not None and cur != prev_key:
            return True
    return False


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[암기] 시작")
    try:
        reset_progress(driver)
        while not stop_event.is_set():
            if check_step2_success_and_stop(driver, stop_event):
                break

            prev = get_card_key(driver)

            if prev is None:
                # 카드 식별 불가(페이지 구조 차이) → 기존 타이머 방식
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
                if _wait_with_check(driver, stop_event, total=0.6):
                    break
                ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.SPACE).key_up(Keys.SHIFT).perform()
                if _wait_with_check(driver, stop_event, total=1.3):
                    break
                continue

            # 카드가 실제로 넘어갈 때까지 SPACE→SHIFT+SPACE 재시도 (씹힘 대비, 최대 8회)
            for _ in range(8):
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
                if _wait_change_or_stop(driver, stop_event, prev, total=0.6):
                    break
                ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.SPACE).key_up(Keys.SHIFT).perform()
                if _wait_change_or_stop(driver, stop_event, prev, total=1.3):
                    break
            if stop_event.is_set():
                break

    except Exception as e:
        if not stop_event.is_set():
            print(f"[암기] 오류: {e}")
    finally:
        print("[암기] 종료")
