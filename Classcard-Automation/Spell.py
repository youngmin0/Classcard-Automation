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

# --- 🎯 사용자 설정 영역 ---

# 1. 자동화할 클래스카드 스펠 URL
URL = 'https://www.classcard.net//Login'


# --- 코드 본문 ---

def get_screen_text(driver):
    try:
        wait = WebDriverWait(driver, 10)
        target_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.current .spell-content'))
        )
        # 요소의 텍스트를 반환
        return target_element.text
    except TimeoutException:
        print("시간 초과: 문제 텍스트 요소를 찾을 수 없습니다. 페이지가 올바르게 로드되었는지 확인하세요.")
        return None

def create_answer_dict():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'data.json')
        with open(json_path, 'r', encoding='utf-8') as file:
            card_list = json.load(file)
        # 클래스카드 데이터는 'back'이 뜻, 'front'가 단어입니다.
        answer_dict = {item['back']: item['front'] for item in card_list}
        print("정답 딕셔너리 생성 완료! 총", len(answer_dict), "개의 단어가 로드되었습니다.")
        return answer_dict
    except json.JSONDecodeError:
        print("JSON 데이터 형식이 잘못되었습니다. 복사한 데이터를 확인해주세요.")
        return None

def main():
    """메인 자동화 로직을 실행합니다."""
    
    # 1. 정답 딕셔너리 생성
    answer_dict = create_answer_dict()
    if not answer_dict:
        return

    # 2. Selenium 웹 드라이버 설정 및 실행
    chrome_options = Options()

    # ================= 자동화 탐지 우회 =================
    # 1. "Chrome이 자동화된 테스트 소프트웨어에 의해 제어되고 있습니다." 메시지 숨기기
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 2. 브라우저의 navigator.webdriver 값을 false로 설정하여 자동화 탐지 회피
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # 3. 최신 일반 사용자처럼 보이게 할 User-Agent 설정
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    chrome_options.add_argument(f'user-agent={user_agent}')
    # =====================================================================

    chrome_options.add_experimental_option("detach", True) 
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)

    input("\n브라우저에서 스펠 학습 시작 페이지로 이동한 후, 여기에서 Enter 키를 누르면 자동화를 시작합니다...")
    time.sleep(2)
    print("\n자동화를 시작합니다. (종료하려면 Ctrl+C를 누르세요)")
    print("---------------------------------------------------------")
    
    try:
        while True:
            # 1. Selenium으로 화면(웹페이지)에서 문제 텍스트 읽기
            text = get_screen_text(driver)
            if text is None:
                time.sleep(1)
                continue
            
            print(f"1. 인식된 텍스트: '{text}'")

            # 2. 딕셔너리에서 정답 찾기 (공백 등 불일치에 대비)
            found_key = None
            for key in answer_dict.keys():
                # 인식된 텍스트와 딕셔너리 키의 공백을 모두 제거하고 비교
                if ''.join(text.split()) in ''.join(key.split()):
                    found_key = key
                    break
            
            if found_key:
                answer = answer_dict[found_key]
                print(f"2. 정답을 찾았습니다! -> '{answer}'")

                # 3. PyAutoGUI로 정답 입력 및 제출
                print("3. 정답을 입력합니다...")
                pyautogui.click(pyautogui.position())
                time.sleep(0.1)
                pyautogui.write(answer, interval=0.01)
                time.sleep(0.1)
                pyautogui.press('enter')
                
                # 다음 문제로 넘어가는 시간 (네트워크 속도에 따라 조절)
                time.sleep(1.5)
                pyautogui.press('space') # '다음' 버튼 클릭
                print("---------------------------------------------------------")
                time.sleep(1.0) # 다음 문제 로딩 대기
            else:
                print(f"2. 딕셔너리에서 '{text}'에 대한 정답을 찾지 못했습니다.")
                print("---------------------------------------------------------")
                time.sleep(2.5)

    except KeyboardInterrupt:
        print("\n 프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()