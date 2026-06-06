import json
import os
import time
import threading
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchWindowException
from selenium.webdriver.common.keys import Keys


INPUT_SELECTOR = 'input[name="input_answer"]'


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


def get_active_card(driver):
    """현재 카드(.CardItem.current)의 (data-idx, 제시어 텍스트)를 반환.
    제시어는 보이는 .spell-answer .spell-content (한국어 의미). 없으면 (None, None)."""
    try:
        res = driver.execute_script(r'''
            var card = document.querySelector('.CardItem.current');
            if (!card) return null;
            var conts = card.querySelectorAll('.spell-answer .spell-content');
            var prompt = '';
            for (var i = 0; i < conts.length; i++) {
                var t = (conts[i].textContent || '').trim();
                if (t) { prompt = t; break; }
            }
            return {idx: card.getAttribute('data-idx'), prompt: prompt};
        ''')
        if not res:
            return None, None
        return res.get('idx'), (res.get('prompt') or '')
    except NoSuchWindowException:
        raise
    except Exception:
        return None, None


def get_active_input(driver):
    """현재 카드의 '보이는' 입력창을 반환. card-top의 input은 hidden이라 제외해야 함."""
    try:
        for el in driver.find_elements(By.CSS_SELECTOR, '.CardItem.current ' + INPUT_SELECTOR):
            try:
                if el.is_displayed():
                    return el
            except Exception:
                continue
    except NoSuchWindowException:
        raise
    except Exception:
        pass
    # 폴백: 문서 전체에서 보이는 입력창
    try:
        for el in driver.find_elements(By.CSS_SELECTOR, INPUT_SELECTOR):
            if el.is_displayed():
                return el
    except Exception:
        pass
    return None


def find_answer(answer_dict, prompt):
    """제시어(prompt)에 해당하는 입력 정답을 찾는다.
    기본은 back(의미)→front(단어). 단어 제시 모드 대비로 front→back 역방향도 시도."""
    p = ''.join(prompt.split())
    for back, front in answer_dict.items():
        if p == ''.join(back.split()):
            return front
    for back, front in answer_dict.items():
        if p == ''.join(front.split()):
            return back
    return None


def check_step2_success_and_stop(driver, stop_event):
    """`#study_end.active` 또는 `.btn-study-end-repeat`가 보이면 완료. set 페이지로 복귀 후 stop."""
    try:
        done = driver.execute_script('''
            var btns = document.querySelectorAll(".btn-study-end-repeat");
            for (var i = 0; i < btns.length; i++) {
                if (btns[i].offsetParent !== null) return true;
            }
            return document.querySelectorAll("#study_end.active").length > 0;
        ''')
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


def _wait_next_card(driver, stop_event, prev_idx, timeout=2.5):
    """현재 카드(data-idx)가 prev_idx에서 바뀌거나 완료될 때까지 대기.
    반환: 'changed' | 'done' | 'stopped' | 'stuck'"""
    elapsed = 0.0
    while elapsed < timeout:
        if stop_event.wait(timeout=0.2):
            return 'stopped'
        elapsed += 0.2
        if check_step2_success_and_stop(driver, stop_event):
            return 'done'
        idx, _ = get_active_card(driver)
        if idx is not None and idx != prev_idx:
            return 'changed'
    return 'stuck'


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[스펠] 시작")

    if not answer_dict:
        print("[스펠] answer_dict가 없습니다. Ctrl+M으로 단어장을 먼저 가져오세요.")
        return

    try:
        while not stop_event.is_set():
            if check_step2_success_and_stop(driver, stop_event):
                break

            idx, prompt = get_active_card(driver)
            if not prompt:
                if check_step2_success_and_stop(driver, stop_event):
                    break
                if stop_event.wait(timeout=0.4):
                    break
                continue

            input_el = get_active_input(driver)
            if input_el is None:
                if stop_event.wait(timeout=0.3):
                    break
                continue

            answer = find_answer(answer_dict, prompt)
            try:
                input_el.clear()
                if answer:
                    input_el.send_keys(answer)
                    if stop_event.wait(timeout=0.1):
                        break
                    input_el.send_keys(Keys.RETURN)
                else:
                    # 정답을 모르면 빈 입력으로 제출 → 정답 표시 후 다음으로 진행 (무한루프 방지)
                    print(f"[스펠] 매칭 실패(스킵): {prompt!r}")
                    input_el.send_keys(Keys.RETURN)
            except Exception as e:
                print(f"[스펠] 입력 오류: {e}")
                if stop_event.wait(timeout=0.3):
                    break
                continue

            # 다음 카드로 넘어갈 때까지 대기. 안 넘어가면(오답으로 정답 표시 등) 진행 키 한 번 더.
            status = _wait_next_card(driver, stop_event, idx, timeout=2.0)
            if status in ('stopped', 'done'):
                break
            if status == 'stuck':
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
                except Exception:
                    pass
                if _wait_next_card(driver, stop_event, idx, timeout=2.0) in ('stopped', 'done'):
                    break

    except NoSuchWindowException:
        pass
    except Exception as e:
        if not stop_event.is_set():
            print(f"[스펠] 오류: {e}")
    finally:
        print("[스펠] 종료")
