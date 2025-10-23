import time
import json
import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
import os
import threading

# --- 🎯 사용자 설정 영역 ---

# 1. 자동화할 클래스카드 스펠 URL
URL = 'https://www.classcard.net//Login'

# --- 코드 본문 ---

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

##### 메인 코드 복붙해옴
def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    """메인 자동화 로직을 실행합니다."""
    print("\n[ctrl + Y] 자동화를 시작합니다. (종료하려면 'ctrl + E' 키)")
    print("---------------------------------------------------------")

    try:
        while not stop_event.is_set():
            click_answer(driver)
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n 프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n 오류가 발생했습니다: {e}")
