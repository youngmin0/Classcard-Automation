import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchWindowException
import threading


def click_answer(driver):
    try:
        wait = WebDriverWait(driver, 10)

        try:
            wait.until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, '.card-cover.down'))
            )
        except TimeoutException:
            pass

        showing_element = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '.showing'))
        )
        target_element = showing_element.find_element(By.CSS_SELECTOR, '.answer')

        try:
            target_element.click()
        except Exception:
            driver.execute_script("arguments[0].click();", target_element)

    except TimeoutException:
        return None


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
    elapsed = 0.0
    while elapsed < total:
        if stop_event.wait(timeout=min(interval, total - elapsed)):
            return True
        elapsed += interval
        if check_step2_success_and_stop(driver, stop_event):
            return True
    return False


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[리콜] 시작")
    try:
        while not stop_event.is_set():
            if check_step2_success_and_stop(driver, stop_event):
                break
            click_answer(driver)
            if _wait_with_check(driver, stop_event, total=1.5):
                break

    except Exception as e:
        if not stop_event.is_set():
            print(f"[리콜] 오류: {e}")
    finally:
        print("[리콜] 종료")
