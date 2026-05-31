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


def parse_english_words(front_sentence):
    """영어 문장을 클릭 단위 토큰으로 분리. 괄호 `(...)`는 한 덩어리 scramble-item으로 표시되므로 통째로 유지.
    클릭 비교는 알파벳/숫자만 남긴 형태로 한다 (구두점 무시).

    예) "When I looked back (on the old days), it all"
        -> ["When", "I", "looked", "back", "onTheOldDays", "it", "all"]
        "Hello, world! Don't stop."
        -> ["Hello", "world", "Dont", "stop"]
    """
    raw_tokens = re.findall(r'\([^)]*\)|\S+', front_sentence)
    parsed = []
    for token in raw_tokens:
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", token)
        if cleaned:
            parsed.append(cleaned)
    return parsed


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


def click_scramble_word(driver, word):
    try:
        items = driver.find_elements(By.CSS_SELECTOR, ".active .scramble-item:not(.clicked)")
        for item in items:
            item_text = re.sub(r"[^a-zA-Z0-9]", "", item.text.strip())
            if item_text == word:
                try:
                    item.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", item)
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
            if stop_event.wait(timeout=0.5):
                break

            korean_text = get_korean_sentence(driver)
            if korean_text is None:
                if check_step2_success_and_stop(driver, stop_event):
                    break
                if stop_event.wait(timeout=0.5):
                    break
                continue

            found_key = None
            normalized_korean = normalize_text(korean_text)
            for key in answer_dict:
                if normalized_korean == normalize_text(key):
                    found_key = key
                    break

            if not found_key:
                print(f"[문장 암기] 매칭 실패: {korean_text!r}")
                if stop_event.wait(timeout=0.5):
                    break
                continue

            english_sentence = answer_dict[found_key]
            words = parse_english_words(english_sentence)

            for word in words:
                if stop_event.is_set():
                    break
                click_scramble_word(driver, word)
                if stop_event.wait(timeout=0.3):
                    break

            if stop_event.is_set():
                break

            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if stop_event.wait(timeout=0.5):
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
