import time
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchWindowException


def check_step2_success_and_stop(driver, stop_event):
    """완료 종료 판단: `.btn-study-end-repeat` visible / `.next-repeat-percent` >= 100 / `#study_end.active` 중 하나."""
    try:
        done = driver.execute_script('''
            var btns = document.querySelectorAll(".btn-study-end-repeat");
            for (var i = 0; i < btns.length; i++) {
                if (btns[i].offsetParent !== null) return true;
            }
            var ps = document.querySelectorAll(".next-repeat-percent");
            for (var i = 0; i < ps.length; i++) {
                if (ps[i].offsetParent !== null && parseInt(ps[i].textContent) >= 100) return true;
            }
            return document.querySelectorAll("#study_end.active").length > 0;
        ''')
        if not done:
            return False
        driver.execute_script(
            'var a = document.querySelectorAll("#study_end.active .study-header a"); if (a.length) a[0].click();'
        )
        driver.execute_script(
            'var a = document.querySelectorAll(".btn-top-menu a"); if (a.length) a[0].click();'
        )
        time.sleep(0.5)
        driver.execute_script(
            'var a = document.querySelectorAll(".close_o"); if (a.length) a[0].click();'
        )
        stop_event.set()
        return True
    except NoSuchWindowException:
        raise
    except Exception:
        return False


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


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[암기] 시작")
    try:
        while not stop_event.is_set():
            if check_step2_success_and_stop(driver, stop_event):
                break
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if _wait_with_check(driver, stop_event, total=0.6):
                break
            ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.SPACE).key_up(Keys.SHIFT).perform()
            if _wait_with_check(driver, stop_event, total=1.3):
                break

    except Exception as e:
        if not stop_event.is_set():
            print(f"[암기] 오류: {e}")
    finally:
        print("[암기] 종료")
