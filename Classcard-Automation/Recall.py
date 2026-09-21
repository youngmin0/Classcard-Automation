import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchWindowException
import threading

from StudyEnd import check_step2_success_and_stop, reset_progress


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
        reset_progress(driver)
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
