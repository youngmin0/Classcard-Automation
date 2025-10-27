import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import threading

def click_answer(driver):
    try:
        wait = WebDriverWait(driver, 10)
        showing_element = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '.showing'))
        )
        target_element = showing_element.find_element(By.CSS_SELECTOR, '.answer')
        target_element.click()
    except TimeoutException:
        print("시간 초과: 문제 텍스트 요소를 찾을 수 없습니다. 페이지가 올바르게 로드되었는지 확인하세요.")
        return None


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("\n[ctrl + Y] 자동화를 시작합니다. (종료하려면 'ctrl + E' 키)")
    print("---------------------------------------------------------")
    try:
        while not stop_event.is_set():
            click_answer(driver)
            time.sleep(2)
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
