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
    """`.btn-study-end-repeat` 버튼이 보이면 완료. set 페이지로 복귀 후 stop."""
    try:
        done = driver.execute_script(
            'return document.querySelectorAll("#study_end.active .btn-study-end-repeat").length > 0;'
        )
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


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[리콜] 시작")
    try:
        while not stop_event.is_set():
            click_answer(driver)
            time.sleep(1.5)

            if check_step2_success_and_stop(driver, stop_event):
                break

    except Exception as e:
        if not stop_event.is_set():
            print(f"[리콜] 오류: {e}")
    finally:
        print("[리콜] 종료")
