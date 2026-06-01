import re
import unicodedata
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchWindowException


def normalize_text(text):
    """보이지 않는 유니코드 문자와 공백을 모두 제거하여 비교용 문자열로 정규화합니다."""
    # NFKC 정규화: 전각문자/합성문자 등 통일
    text = unicodedata.normalize('NFKC', text)
    # Non-breaking space, Zero-width 계열, BOM 등 제거
    text = re.sub(r'[ ​‌‍\u200E\u200F﻿]', '', text)
    # 나머지 모든 공백 제거
    return "".join(text.split())


def get_korean_sentence(driver):
    """현재 화면의 한글 문장을 가져옵니다. (.active span.para_item)"""
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, ".active span.para_item")
        if not elements:
            return None
        # 여러 span이 있을 경우 공백으로 합쳐서 한 문장으로 구성
        text = " ".join(el.text.strip() for el in elements if el.text.strip())
        return text if text else None
    except NoSuchWindowException:
        raise
    except Exception as e:
        print(f"한글 문장 읽기 오류: {e}")
        return None


def parse_english_words(front_sentence):
    """영어 문장을 단어로 분리하고 알파벳만 남깁니다.

    예) "Hello, world! Don't stop." -> ["Hello", "world", "Dont", "stop"]
    """
    tokens = front_sentence.split()
    parsed = []
    for token in tokens:
        parts = re.split(r'(\([^)]*\))', token)
        for part in parts:
            cleaned = re.sub(r"[^a-zA-Z0-9]", "", part)
            if cleaned:
                parsed.append(cleaned)
    return parsed


def check_step2_success_and_stop(driver, stop_event):
    """완료 후 .hidden.step2 .text-success 가 없으면 원격 버튼을 클릭하고 자동화를 중지합니다."""
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
            return True  # 중지 신호 발생
        else:
            print(f"  [체크] .hidden.step2 존재 ({success_elements}개) → 계속 진행")
            return False
    except NoSuchWindowException:
        raise
    except Exception as e:
        print(f"  [체크] 완료 확인 중 오류: {e}")
        return False


def click_scramble_word(driver, word):
    """현재 scramble-item 목록에서 해당 단어를 찾아 클릭합니다.

    같은 단어가 여러 개 있을 경우 첫 번째 항목을 클릭합니다.
    """
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
        print(f"  [!] 단어를 찾지 못했습니다: '{word}'")
        return False
    except NoSuchWindowException:
        raise
    except Exception as e:
        print(f"  단어 클릭 오류 ({word}): {e}")
        return False


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("\n[문장 암기 자동화 시작] (종료하려면 'ctrl + E' 키)")
    print("---------------------------------------------------------")

    try:
        while not stop_event.is_set():
            # 1. 문장 시작 시 space 누르기
            print("[시작] space 키 입력")
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if stop_event.wait(timeout=0.5):
                break

            # 2. 현재 화면의 한글 문장 읽기
            korean_text = get_korean_sentence(driver)
            if korean_text is None:
                if stop_event.wait(timeout=0.3):
                    break
                continue

            print(f"\n[한글 문장] {korean_text}")

            # 3. data.json(answer_dict)에서 대응하는 영어 문장 찾기
            found_key = None
            normalized_korean = normalize_text(korean_text)
            for key in answer_dict:
                if normalized_korean == normalize_text(key):
                    found_key = key
                    break

            if not found_key:
                print(f"  [!] 딕셔너리에서 대응하는 영어 문장을 찾지 못했습니다.")
                print(f"  [디버그] 화면 텍스트 (repr): {repr(korean_text)}")
                if stop_event.wait(timeout=0.3):
                    break
                continue

            english_sentence = answer_dict[found_key]
            print(f"[영어 문장] {english_sentence}")

            # 4. 영어 문장을 단어 단위로 파싱 (알파벳만 남기기)
            words = parse_english_words(english_sentence)
            print(f"[파싱 결과] {words}")

            # 5. 파싱된 단어 순서대로 scramble-item 클릭 (단어 사이 1초 대기)
            for word in words:
                if stop_event.is_set():
                    break
                success = click_scramble_word(driver, word)
                if success:
                    print(f"  클릭: {word}")
                if stop_event.wait(timeout=0.1):
                    break

            if stop_event.is_set():
                break

            # 6. 문장 완료 후 space 누르고 1초 대기 후 다음 문장으로
            print("[완료] 문장 입력 완료. space 키 입력 후 다음 문장으로 이동합니다...")
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if stop_event.wait(timeout=0.3):
                break

            # 7. step2 성공 여부 확인 → 없으면 버튼 클릭 후 자동화 중지
            if check_step2_success_and_stop(driver, stop_event):
                break

    except NoSuchWindowException:
        if not stop_event.is_set():
            print("\n브라우저 창이 닫혀 자동화를 중지합니다.")
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
