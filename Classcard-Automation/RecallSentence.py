import re
import threading
from itertools import permutations as iperms
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchWindowException


def tokenize(text):
    """텍스트를 토큰 리스트로 분리합니다.
    - 띄어쓰기로 1차 분리
    - 쉼표·마침표 등 구두점은 그대로 유지
    - 'in(to)' 처럼 단어 중간에 '('가 있으면 앞에서 추가 분리
      예) 'in(to)' → ['in', '(to)']
    """
    words = text.split()
    tokens = []
    for word in words:
        # 단어 중간(앞에 비공백 문자가 있는) '(' 앞에서 분리
        parts = re.split(r'(?<=\S)(?=\()', word)
        tokens.extend(p for p in parts if p)
    return tokens


def get_prefix_tokens(driver):
    """.active .input-box에 이미 배치된 접두사 토큰들을 가져옵니다."""
    try:
        input_box = driver.find_element(By.CSS_SELECTOR, ".active .input-box")
        text = input_box.text.strip()[:-1]
        if not text:
            return []
        return tokenize(text)
    except NoSuchWindowException:
        raise
    except Exception as e:
        print(f"접두사 읽기 오류: {e}")
        return []


def get_available_tokens(driver):
    """현재 클릭 가능한 .btn-scramble.clickable 버튼들의 텍스트를 리스트로 반환합니다."""
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, ".btn-scramble.clickable")
        return [btn.text.strip() for btn in buttons if btn.text.strip()]
    except NoSuchWindowException:
        raise
    except Exception as e:
        print(f"가용 버튼 읽기 오류: {e}")
        return []


def find_matching_sentences(prefix_tokens, answer_dict):
    """접두사 토큰들에 매칭되는 영어 문장을 answer_dict에서 모두 찾아 리스트로 반환합니다.
    대소문자는 무시하고 비교합니다.
    """
    n = len(prefix_tokens)
    if n == 0:
        return []

    lower_prefix = [t.lower() for t in prefix_tokens]
    matches = []

    for sentence in answer_dict.values():
        sentence_tokens = tokenize(sentence)
        if len(sentence_tokens) < n:
            continue
        if [t.lower() for t in sentence_tokens[:n]] == lower_prefix:
            matches.append(sentence)

    return matches


def find_matching_sentence_fallback(prefix_tokens, available_tokens, answer_dict):
    """접두사가 여러 문장에 중의적으로 매칭될 때 사용하는 폴백.
    available_tokens에서 4개를 뽑아 4!(= 24)가지 순열로 접두사 뒤에 이어붙여
    정확히 하나의 문장 접두사와 일치하는 경우를 찾습니다.
    """
    n = min(4, len(available_tokens))
    if n == 0:
        return None

    lower_prefix = [t.lower() for t in prefix_tokens]

    for perm in iperms(available_tokens, n):
        candidate = lower_prefix + [t.lower() for t in perm]
        candidate_len = len(candidate)

        matched = []
        for sentence in answer_dict.values():
            sentence_tokens = tokenize(sentence)
            if len(sentence_tokens) < candidate_len:
                continue
            if [t.lower() for t in sentence_tokens[:candidate_len]] == candidate:
                matched.append(sentence)

        if len(matched) == 1:
            return matched[0]

    return None


def check_step2_success_and_stop(driver, stop_event):
    """완료 후 .hidden.step2 가 없으면 원격 버튼을 클릭하고 자동화를 중지합니다."""
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
            return True
        else:
            print(f"  [체크] .hidden.step2 존재 ({success_elements}개) → 계속 진행")
            return False
    except NoSuchWindowException:
        raise
    except Exception as e:
        print(f"  [체크] 완료 확인 중 오류: {e}")
        return False


def click_remaining_tokens(driver, remaining_tokens, stop_event):
    """남은 토큰들을 .btn-scramble.clickable에서 찾아 순서대로 클릭합니다.
    버튼 텍스트와 토큰을 그대로(구두점 포함) 비교합니다.
    """
    for token in remaining_tokens:
        if stop_event.is_set():
            break

        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, ".btn-scramble.clickable:not(.clicked)")
            clicked = False
            for btn in buttons:
                if btn.text.strip() == token:
                    try:
                        btn.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", btn)
                    print(f"  클릭: {token}")
                    clicked = True
                    break

            if not clicked:
                # 대소문자 무시 폴백
                for btn in buttons:
                    if btn.text.strip().lower() == token.lower():
                        try:
                            btn.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", btn)
                        print(f"  클릭(대소문자 무시): {token}")
                        clicked = True
                        break

            if not clicked:
                print(f"  [!] 버튼을 찾지 못했습니다: '{token}'")

        except NoSuchWindowException:
            raise
        except Exception as e:
            print(f"  단어 클릭 오류 ({token}): {e}")

        # 0.3초 간격
        if stop_event.wait(timeout=0.3):
            break


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("\n[문장 리콜 자동화 시작] (종료하려면 'ctrl + E' 키)")
    print("---------------------------------------------------------")

    try:
        while not stop_event.is_set():
            # 1. 접두사 토큰 읽기
            prefix_tokens = get_prefix_tokens(driver)
            if not prefix_tokens:
                if stop_event.wait(timeout=0.5):
                    break
                continue

            print(f"\n[접두사] {prefix_tokens}")

            # 2. 접두사에 매칭되는 영어 문장 찾기
            matches = find_matching_sentences(prefix_tokens, answer_dict)

            if len(matches) == 1:
                sentence = matches[0]
            elif len(matches) > 1:
                # 2-1. 여러 문장이 매칭되면 순열로 범위를 좁힘
                available_tokens = get_available_tokens(driver)
                print(f"  [중의적 접두사] {len(matches)}개 매칭 → 가용 버튼 {len(available_tokens)}개로 4-순열 탐색 중...")
                sentence = find_matching_sentence_fallback(
                    prefix_tokens, available_tokens, answer_dict
                )
            else:
                sentence = None

            if not sentence:
                print(f"  [!] 접두사에 매칭되는 문장을 찾지 못했습니다.")
                if stop_event.wait(timeout=0.5):
                    break
                continue

            print(f"[문장] {sentence}")

            # 3. 전체 토큰에서 접두사 이후의 남은 토큰들 추출
            all_tokens = tokenize(sentence)
            remaining_tokens = all_tokens[len(prefix_tokens):]
            print(f"[남은 토큰] {remaining_tokens}")

            # 4. 남은 토큰들을 .btn-scramble.clickable에서 순서대로 클릭
            click_remaining_tokens(driver, remaining_tokens, stop_event)

            if stop_event.is_set():
                break

            # 5. 완료 후 space 누르기
            print("[완료] space 키 입력")
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if stop_event.wait(timeout=1.0):
                break

            # 6. step2 성공 여부 확인 → 없으면 버튼 클릭 후 자동화 중지
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
