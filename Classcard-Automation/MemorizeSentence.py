import re
import time
import unicodedata
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchWindowException


def normalize_text(text):
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'[ ​‌‍‎‏﻿]', '', text)
    return "".join(text.split())


def get_korean_sentence(driver):
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, ".active span.para_item")
        if not elements:
            return None
        text = " ".join(el.text.strip() for el in elements if el.text.strip())
        return text if text else None
    except NoSuchWindowException:
        raise
    except Exception:
        return None


def get_active_english(driver):
    """현재 카드의 영어 정답 문장을 DOM에서 직접 읽는다 (data.json 불필요).
    같은 .CardItem.active 안 step s1의 .text 에 정답 영어 문장이 들어있다."""
    try:
        return driver.execute_script(r'''
            var card = document.querySelector('.CardItem.active');
            if (!card) return null;
            var t = card.querySelector('.step.s1 .front .text') || card.querySelector('.text');
            return t ? (t.textContent || '').trim() : null;
        ''')
    except NoSuchWindowException:
        raise
    except Exception:
        return None


def parse_english_words(front_sentence):
    """영어 문장을 raw 토큰으로 분리 (괄호 묶음은 통째). 클릭 매칭은 click_scramble_word가 담당."""
    return re.findall(r'\([^)]*\)|\S+', front_sentence)


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


def _click_item(driver, item):
    try:
        item.click()
    except Exception:
        driver.execute_script("arguments[0].click();", item)


def _try_click_token(driver, raw_token):
    """단일 raw_token으로 화면 scramble-item 한 개 매칭+클릭. 못 찾으면 False."""
    items = driver.find_elements(By.CSS_SELECTOR, ".active .scramble-item:not(.clicked)")
    if raw_token in ('-', '–', '—'):
        for item in items:
            if item.text.strip() in ('-', '–', '—'):
                _click_item(driver, item)
                return True
        return False
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", raw_token)
    if not cleaned:
        return False
    for item in items:
        if re.sub(r"[^a-zA-Z0-9]", "", item.text.strip()) == cleaned:
            _click_item(driver, item)
            return True
    return False


def click_scramble_word(driver, raw_token):
    """raw_token으로 클릭 시도. 통째 매칭 실패 시 하이픈/괄호로 분리해 부분 매칭 폴백."""
    try:
        if _try_click_token(driver, raw_token):
            return True

        if re.search(r'[-–—]', raw_token):
            any_clicked = False
            for sub in re.split(r'([-–—])', raw_token):
                if not sub:
                    continue
                if _try_click_token(driver, sub):
                    any_clicked = True
                    time.sleep(0.15)
            if any_clicked:
                return True

        if '(' in raw_token and ')' in raw_token:
            any_clicked = False
            for sub in re.split(r'(\([^)]*\))', raw_token):
                if not sub:
                    continue
                if _try_click_token(driver, sub):
                    any_clicked = True
                    time.sleep(0.15)
            if any_clicked:
                return True

        return False
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[문장 암기] 시작")

    try:
        while not stop_event.is_set():
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if stop_event.wait(timeout=0.3):
                break
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if stop_event.wait(timeout=0.3):
                break

            # 1) 정답 영어 문장: DOM에서 직접 읽기 (data.json 불필요)
            english_sentence = get_active_english(driver)

            # 2) 폴백: DOM에서 못 읽으면 한국어 → data.json 매칭
            if not english_sentence and answer_dict:
                korean_text = get_korean_sentence(driver)
                if korean_text:
                    normalized_korean = normalize_text(korean_text)
                    for key in answer_dict:
                        if normalized_korean == normalize_text(key):
                            english_sentence = answer_dict[key]
                            break

            if not english_sentence:
                if check_step2_success_and_stop(driver, stop_event):
                    break
                if stop_event.wait(timeout=0.3):
                    break
                continue

            words = parse_english_words(english_sentence)

            for word in words:
                if stop_event.is_set():
                    break
                # 타일이 7개씩 창처럼 보여 아직 안 나타났을 수 있으니 재시도
                for _ in range(10):
                    if click_scramble_word(driver, word):
                        break
                    if stop_event.wait(timeout=0.2):
                        break
                if stop_event.wait(timeout=0.15):
                    break

            if stop_event.is_set():
                break

            
            if stop_event.wait(timeout=0.3):
                break
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if stop_event.wait(timeout=0.3):
                break

            if check_step2_success_and_stop(driver, stop_event):
                break

    except NoSuchWindowException:
        pass
    except Exception as e:
        if not stop_event.is_set():
            print(f"[문장 암기] 오류: {e}")
    finally:
        print("[문장 암기] 종료")
