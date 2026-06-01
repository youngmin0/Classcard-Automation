import time
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchWindowException


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
    print("[암기] 시작")
    try:
        while not stop_event.is_set():
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            time.sleep(0.6)
            ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.SPACE).key_up(Keys.SHIFT).perform()
            time.sleep(1.3)

            if check_step2_success_and_stop(driver, stop_event):
                break

    except Exception as e:
        if not stop_event.is_set():
            print(f"[암기] 오류: {e}")
    finally:
        print("[암기] 종료")
