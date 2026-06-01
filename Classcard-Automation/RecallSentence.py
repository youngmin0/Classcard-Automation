import re
import time
import threading
from itertools import permutations as iperms
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchWindowException


def tokenize(text):
    """텍스트를 토큰으로 분리. 'in(to)' 처럼 단어 중간의 '(' 앞에서 추가 분리."""
    words = text.split()
    tokens = []
    for word in words:
        parts = re.split(r'(?<=\S)(?=\()', word)
        tokens.extend(p for p in parts if p)
    return tokens


def strip_parens(text):
    """`(...)` 형태의 괄호 부분과 주변 공백을 제거하고 공백을 정리."""
    text = re.sub(r'\s*\([^)]*\)\s*', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def tokenize_loose(text):
    """tokenize + 단어 뒤에 붙은 구두점(,.!?;:)을 별도 토큰으로 분리."""
    result = []
    for t in tokenize(text):
        m = re.match(r'^(.+?)([,.!?;:]+)$', t)
        if m and re.search(r'\w', m.group(1)):
            result.append(m.group(1))
            result.append(m.group(2))
        else:
            result.append(t)
    return result


def is_prefix_punct_split(prefix_tokens):
    """prefix에 단독 구두점 토큰이 있으면 화면이 구두점을 분리해서 표시한 것."""
    return any(re.fullmatch(r'[,.!?;:]+', t) for t in prefix_tokens)


def find_subsequence_end(prefix_tokens, sentence_tokens) -> int:
    """prefix_tokens가 sentence_tokens의 부분 수열이면 마지막 매칭 인덱스, 아니면 -1.
    대소문자 무시."""
    p_low = [t.lower() for t in prefix_tokens]
    if not p_low:
        return -1
    i = 0
    last = -1
    for idx, t in enumerate(sentence_tokens):
        if t.lower() == p_low[i]:
            last = idx
            i += 1
            if i == len(p_low):
                return last
    return -1


def get_prefix_tokens(driver):
    try:
        input_box = driver.find_element(By.CSS_SELECTOR, ".active .input-box")
        text = input_box.text.strip()[:-1]
        if not text:
            return []
        return tokenize(text)
    except NoSuchWindowException:
        raise
    except Exception:
        return []


def get_available_tokens(driver):
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, ".btn-scramble.clickable")
        return [btn.text.strip() for btn in buttons if btn.text.strip()]
    except NoSuchWindowException:
        raise
    except Exception:
        return []


def find_matching_sentences(prefix_tokens, answer_dict, tokenize_fn=tokenize):
    n = len(prefix_tokens)
    if n == 0:
        return []

    lower_prefix = [t.lower() for t in prefix_tokens]
    matches = []

    for sentence in answer_dict.values():
        sentence_tokens = tokenize_fn(sentence)
        if len(sentence_tokens) < n:
            continue
        if [t.lower() for t in sentence_tokens[:n]] == lower_prefix:
            matches.append(sentence)

    return matches


def find_matching_sentence_fallback(prefix_tokens, available_tokens, answer_dict, tokenize_fn=tokenize):
    n = min(4, len(available_tokens))
    if n == 0:
        return None

    lower_prefix = [t.lower() for t in prefix_tokens]

    for perm in iperms(available_tokens, n):
        candidate = lower_prefix + [t.lower() for t in perm]
        candidate_len = len(candidate)

        matched = []
        for sentence in answer_dict.values():
            sentence_tokens = tokenize_fn(sentence)
            if len(sentence_tokens) < candidate_len:
                continue
            if [t.lower() for t in sentence_tokens[:candidate_len]] == candidate:
                matched.append(sentence)

        if len(matched) == 1:
            return matched[0]

    return None


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


def _click_button(driver, btn):
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)


def click_remaining_tokens(driver, remaining_tokens, stop_event):
    """화면 가용 scramble 버튼에 있는 토큰만 순서대로 클릭.

    매칭 우선순위: 정확 일치 → 대소문자 무시 → 구두점 무시(알파벳/숫자만 비교).
    화면에 없는 단어 토큰이 나오면 즉시 break (다음 사이클에서 prefix 재읽고 진행).
    단독 구두점 토큰은 화면에 별도 버튼이 없는 게 정상이므로 skip만 하고 다음 토큰으로.
    """
    for token in remaining_tokens:
        if stop_event.is_set():
            break

        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, ".btn-scramble.clickable:not(.clicked)")
            if not buttons:
                break

            clicked = False

            for btn in buttons:
                if btn.text.strip() == token:
                    _click_button(driver, btn)
                    clicked = True
                    break

            if not clicked:
                for btn in buttons:
                    if btn.text.strip().lower() == token.lower():
                        _click_button(driver, btn)
                        clicked = True
                        break

            if not clicked:
                token_clean = re.sub(r"[^a-zA-Z0-9]", "", token).lower()
                if token_clean:
                    for btn in buttons:
                        btn_clean = re.sub(r"[^a-zA-Z0-9]", "", btn.text.strip()).lower()
                        if btn_clean == token_clean:
                            _click_button(driver, btn)
                            clicked = True
                            break

            if not clicked:
                if re.fullmatch(r'[,.!?;:]+', token):
                    continue
                break

        except NoSuchWindowException:
            raise
        except Exception:
            pass


        if stop_event.wait(timeout=0.3):
            break


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[문장 리콜] 시작")

    try:
        while not stop_event.is_set():
            prefix_tokens = get_prefix_tokens(driver)
            if not prefix_tokens:
                if check_step2_success_and_stop(driver, stop_event):
                    break
                if stop_event.wait(timeout=0.5):
                    break
                continue

            tokenize_fn = tokenize_loose if is_prefix_punct_split(prefix_tokens) else tokenize

            matches = find_matching_sentences(prefix_tokens, answer_dict, tokenize_fn)
            working_dict = answer_dict

            if not matches:
                working_dict = {k: strip_parens(v) for k, v in answer_dict.items()}
                matches = find_matching_sentences(prefix_tokens, working_dict, tokenize_fn)

            sentence = None
            subseq_end = -1

            if len(matches) == 1:
                sentence = matches[0]
            elif len(matches) > 1:
                available_tokens = get_available_tokens(driver)
                sentence = find_matching_sentence_fallback(
                    prefix_tokens, available_tokens, working_dict, tokenize_fn
                )

            if not sentence:
                candidates = []
                for s in working_dict.values():
                    s_tokens = tokenize_fn(s)
                    end = find_subsequence_end(prefix_tokens, s_tokens)
                    if end >= 0:
                        candidates.append((s, end, s_tokens))
                if candidates:
                    candidates.sort(key=lambda c: len(c[2]))
                    sentence, subseq_end, _ = candidates[0]
                    print(f"[문장 리콜] subsequence 매칭")

            if not sentence:
                print(f"[문장 리콜] 매칭 실패: {prefix_tokens}")
                if stop_event.wait(timeout=0.5):
                    break
                continue

            all_tokens = tokenize_fn(sentence)
            if subseq_end >= 0:
                remaining_tokens = all_tokens[subseq_end + 1:]
            else:
                remaining_tokens = all_tokens[len(prefix_tokens):]

            click_remaining_tokens(driver, remaining_tokens, stop_event)

            if stop_event.is_set():
                break

            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if stop_event.wait(timeout=1.0):
                break

            if check_step2_success_and_stop(driver, stop_event):
                break

    except NoSuchWindowException:
        pass
    except Exception as e:
        if not stop_event.is_set():
            print(f"[문장 리콜] 오류: {e}")
    finally:
        print("[문장 리콜] 종료")
