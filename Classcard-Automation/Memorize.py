import time
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchWindowException


def check_step2_success_and_stop(driver, stop_event):
    """완료 후 .hidden.step2 가 없으면 원격 버튼을 클릭하고 자동화를 중지합니다."""
    try:
        success_elements = driver.execute_script(
            'return document.querySelectorAll(".hidden.step2").length;'
        )
        if success_elements == 0:
            print("  [체크] .hidden.step2 없음 → 원격 버튼 클릭 후 자동화 중지")
            remote_items = driver.execute_script(
                'return document.querySelectorAll("#study_end.active .study-header a");'
            )
            if remote_items:
                driver.execute_script(
                    'document.querySelectorAll("#study_end.active .study-header a")[0].click();'
                )
                print("  [체크] 첫 번째 remote_left 버튼 클릭 완료")
            else:
                print("  [체크] remote_left 버튼을 찾지 못했습니다.")
            stop_event.set()
            return True
        else:
            print(f"  [체크] .hidden.step2 존재 ({success_elements}개) → 계속 진행")
            return False
    except NoSuchWindowException:
        raise
    except Exception as e:
        print(f"  [체크] 완료 확인 중 오류: {e}")
        return False


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("\n[ctrl + I] 자동화를 시작합니다. (종료하려면 'ctrl + E' 키)")
    print("---------------------------------------------------------")
    try:
        while not stop_event.is_set():
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            time.sleep(1)
            ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.SPACE).key_up(Keys.SHIFT).perform()
            time.sleep(2)

            if check_step2_success_and_stop(driver, stop_event):
                break

    except Exception as e:
        if not stop_event.is_set():
            print(f"\n자동화 루프 중 오류 발생: {e}")
            if "target window is closed" in str(e) or "invalid session id" in str(e):
                print("브라우저 창이 닫혀 자동화를 중지합니다.")

    finally:
        if stop_event.is_set():
            print("\n[ctrl + E] 자동화 중지 신호를 받았습니다. 루프를 종료합니다.")
        else:
            print("\n자동화 루프가 종료되었습니다.")
