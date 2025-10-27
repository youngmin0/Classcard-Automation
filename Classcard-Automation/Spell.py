import json
import pyautogui
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchWindowException
import os
import threading

def get_screen_text(driver):
    try:
        wait = WebDriverWait(driver, 10)
        target_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.current .spell-content'))
        )
        return target_element.text
    except TimeoutException:
        print("시간 초과: 문제 텍스트 요소를 찾을 수 없습니다.")
        return None
    except NoSuchWindowException:
        print("오류: 브라우저 창이 닫혔습니다.")
        return None
    except Exception as e:
        print(f"텍스트 읽기 오류: {e}")
        return None

def create_answer_dict():
    try:
        json_path = os.path.join(os.getcwd(), 'data.json')
        
        with open(json_path, 'r', encoding='utf-8') as file:
            card_list = json.load(file)
        
        answer_dict = {item['back']: item['front'] for item in card_list}
        print(f"정답 딕셔너리 생성 완료! 총 {len(answer_dict)}개의 단어가 로드되었습니다.")
        return answer_dict
    except FileNotFoundError:
        print(f"오류: {json_path} 에서 data.json 파일을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        print("JSON 데이터 형식이 잘못되었습니다. 복사한 데이터를 확인해주세요.")
        return None

def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("\n[ctrl + X] 자동화를 시작합니다. (종료하려면 'ctrl + E' 키)")
    print("---------------------------------------------------------")
    
    try:
        while not stop_event.is_set():
            
            text = get_screen_text(driver)
            if text is None:
                if stop_event.wait(timeout=1.0): break
                continue
            
            print(f"1. 인식된 텍스트: '{text}'")

            found_key = None
            for key in answer_dict.keys():
                if ''.join(text.split()) == ''.join(key.split()):
                    found_key = key
                    break
            
            if found_key:
                answer = answer_dict[found_key]
                print(f"2. 정답을 찾았습니다! -> '{answer}'")

                print("3. 정답을 입력합니다...")
                pyautogui.click(pyautogui.position())
                if stop_event.wait(timeout=0.1): break
                
                pyautogui.write(answer, interval=0.01)
                if stop_event.wait(timeout=0.1): break
                
                pyautogui.press('enter')
                
                if stop_event.wait(timeout=1.5): break
                pyautogui.press('space')
                print("---------------------------------------------------------")
                if stop_event.wait(timeout=1.0): break
            else:
                print(f"2. 딕셔너리에서 '{text}'에 대한 정답을 찾지 못했습니다.")
                print("---------------------------------------------------------")
                if stop_event.wait(timeout=2.5): break

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