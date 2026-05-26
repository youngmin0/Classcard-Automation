import time
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("\n[ctrl + I] 자동화를 시작합니다. (종료하려면 'ctrl + E' 키)")
    print("---------------------------------------------------------")
    try:
        while not stop_event.is_set():
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            time.sleep(1)
            ActionChains(driver).key_down(Keys.SHIFT).send_keys(Keys.SPACE).key_up(Keys.SHIFT).perform()
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

