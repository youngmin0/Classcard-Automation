import json
import os
import time
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchWindowException
from selenium.webdriver.common.keys import Keys


SPELL_CONTENT_SELECTOR = '.current .spell-content, .spell-content'
INPUT_SELECTOR = 'input[name="input_answer"]'


def get_screen_text(driver):
    try:
        wait = WebDriverWait(driver, 10)
        target_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SPELL_CONTENT_SELECTOR))
        )
        return target_element.text
    except TimeoutException:
        return None
    except NoSuchWindowException:
        return None
    except Exception:
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
        print(f"오류: data.json 파일을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        print("JSON 데이터 형식이 잘못되었습니다.")
        return None


def check_step2_success_and_stop(driver, stop_event):
    """`#study_end.active` 가 있으면 학습 종료로 간주. set 페이지로 복귀 후 stop."""
    try:
        done = driver.execute_script(
            'return document.querySelectorAll("#study_end.active").length > 0;'
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
    print("[스펠] 시작")

    try:
        while not stop_event.is_set():
            text = get_screen_text(driver)
            if text is None:
                if check_step2_success_and_stop(driver, stop_event):
                    break
                if stop_event.wait(timeout=0.5):
                    break
                continue

            found_key = None
            text_norm = ''.join(text.split())
            for key in answer_dict.keys():
                if text_norm == ''.join(key.split()):
                    found_key = key
                    break

            if not found_key:
                print(f"[스펠] 매칭 실패: {text!r}")
                if stop_event.wait(timeout=1.0):
                    break
                continue

            answer = answer_dict[found_key]
            try:
                input_el = driver.find_element(By.CSS_SELECTOR, INPUT_SELECTOR)
                input_el.clear()
                input_el.send_keys(answer)
                if stop_event.wait(timeout=0.1):
                    break
                input_el.send_keys(Keys.RETURN)
            except Exception as e:
                print(f"[스펠] 입력 오류: {e}")
                if stop_event.wait(timeout=0.2):
                    break
                continue

            if stop_event.wait(timeout=1.0):
                break
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if stop_event.wait(timeout=0.7):
                break

            if check_step2_success_and_stop(driver, stop_event):
                break

    except Exception as e:
        if not stop_event.is_set():
            print(f"[스펠] 오류: {e}")
    finally:
        print("[스펠] 종료")
