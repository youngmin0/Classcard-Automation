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


_UNICODE_NORMALIZE = {
    '‘': "'", '’': "'", '‚': "'", '‛': "'",
    '“': '"', '”': '"', '„': '"', '‟': '"',
    '–': '-', '—': '-', '−': '-',
    '…': '...',
}


def normalize_unicode(text):
    """유니코드 인용부호/대시를 ASCII 등가물로 정규화."""
    for k, v in _UNICODE_NORMALIZE.items():
        text = text.replace(k, v)
    return text


def tokenize_loose(text):
    """tokenize + 하이픈/대시/따옴표·끝 구두점(,.!?;:)을 별도 토큰으로 분리."""
    result = []
    for t in tokenize(text):
        for piece in re.split(r"([-–—'\"])", t):
            if not piece:
                continue
            m = re.match(r'^(.+?)([,.!?;:]+)$', piece)
            if m and re.search(r'\w', m.group(1)):
                result.append(m.group(1))
                result.append(m.group(2))
            else:
                result.append(piece)
    return result


def is_prefix_punct_split(prefix_tokens):
    """prefix에 단독 구두점/하이픈/따옴표 토큰이 있으면 화면이 분리해서 표시한 것."""
    return any(re.fullmatch(r"[,.!?;:\-–—'\"]+", t) for t in prefix_tokens)


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


def get_page_answers(driver):
    """페이지가 console.log('arr_front', ...)로 출력한 정답을 캡처해둔
    window.__cc_answers(영어 문장 리스트)를 읽는다. (main.py가 console.log를 후킹)
    중복 제거하여 반환. 없으면 None."""
    try:
        arr = driver.execute_script(
            "return (window.__cc_answers && window.__cc_answers.length) ? window.__cc_answers : null;"
        )
    except NoSuchWindowException:
        raise
    except Exception:
        return None
    if not arr:
        return None
    seen, out = set(), []
    for s in arr:
        s = (s or '').strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out or None


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


def has_active_input(driver):
    """현재 풀고 있는 카드의 input-box가 화면에 있는지 (게임 진행 중인지)."""
    try:
        return len(driver.find_elements(By.CSS_SELECTOR, ".active .input-box")) > 0
    except NoSuchWindowException:
        raise
    except Exception:
        return False


def _wkey(token):
    """단어 비교 키: 유니코드 정규화 + 영숫자만 + 소문자."""
    return re.sub(r'[^a-z0-9]', '', normalize_unicode(token).lower())


def find_sentence_by_candidates(available_tokens, sent_dict, tokenize_fn):
    """빈 prefix(문장 시작): 후보 단어 멀티셋이 어떤 문장의 앞 k개 토큰과 일치하는지로 식별.
    유일 매칭이면 그 문장, 여러 개여도 첫 단어가 모두 같으면 그 문장 반환. 못 정하면 None."""
    cand = sorted(filter(None, (_wkey(t) for t in available_tokens)))
    if not cand:
        return None
    k = len(available_tokens)
    matched = []
    for s in sent_dict.values():
        toks = tokenize_fn(s)
        if len(toks) < k:
            continue
        head = sorted(filter(None, (_wkey(t) for t in toks[:k])))
        if head == cand:
            matched.append(s)
    if len(matched) == 1:
        return matched[0]
    if len(matched) > 1:
        firsts = {_wkey(tokenize_fn(s)[0]) for s in matched if tokenize_fn(s)}
        if len(firsts) == 1:
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

    매칭 우선순위: 정확 일치(정규화) → 대소문자 무시 → 구두점 무시(알파벳/숫자만 비교).
    화면에 없는 단어 토큰이 나오면 즉시 break.
    단독 구두점/하이픈 토큰은 화면에 별도 버튼이 없는 게 정상이므로 skip만 하고 다음 토큰으로.
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
                if normalize_unicode(btn.text.strip()) == token:
                    _click_button(driver, btn)
                    clicked = True
                    break

            if not clicked:
                for btn in buttons:
                    if normalize_unicode(btn.text.strip()).lower() == token.lower():
                        _click_button(driver, btn)
                        clicked = True
                        break

            if not clicked:
                token_clean = re.sub(r"[^a-zA-Z0-9]", "", token).lower()
                if token_clean:
                    for btn in buttons:
                        btn_clean = re.sub(r"[^a-zA-Z0-9]", "", normalize_unicode(btn.text.strip())).lower()
                        if btn_clean == token_clean:
                            _click_button(driver, btn)
                            clicked = True
                            break

            if not clicked:
                if re.fullmatch(r'[,.!?;:\-–—\'"]+', token):
                    continue
                break

        except NoSuchWindowException:
            raise
        except Exception:
            pass


        if stop_event.wait(timeout=0.2):
            break


def run_automation_loop(driver, answer_dict, stop_event: threading.Event):
    print("[문장 리콜] 시작")

    # 페이지가 정답을 로그할 때까지 잠깐 대기 (console.log 후킹 캡처)
    captured_logged = False
    for _ in range(20):
        if get_page_answers(driver):
            print("[문장 리콜] 페이지 정답 캡처 성공 (data.json 불필요)")
            captured_logged = True
            break
        if stop_event.wait(timeout=0.3):
            return
    if not captured_logged and not answer_dict:
        print("[문장 리콜] 정답 소스 없음 (캡처 실패 & data.json 없음). 종료")
        return

    try:
        while not stop_event.is_set():
            # 매 카드마다 캡처된 정답 우선, 없으면 data.json 폴백
            page_answers = get_page_answers(driver)
            active_dict = ({i: s for i, s in enumerate(page_answers)}
                           if page_answers else (answer_dict or {}))
            if not active_dict:
                if check_step2_success_and_stop(driver, stop_event):
                    break
                if stop_event.wait(timeout=0.3):
                    break
                continue

            prefix_tokens = get_prefix_tokens(driver)
            if not prefix_tokens:
                # 카드가 없으면(전환/종료) 종료 체크
                if not has_active_input(driver):
                    if check_step2_success_and_stop(driver, stop_event):
                        break
                    if stop_event.wait(timeout=0.3):
                        break
                    continue

                # 문장 시작(빈 prefix): 후보 단어로 문장을 식별해 처음부터 클릭
                available_tokens = [normalize_unicode(t) for t in get_available_tokens(driver)]
                start_fn = (tokenize_loose
                            if any(re.fullmatch(r"[,.!?;:\-–—'\"]+", t) for t in available_tokens)
                            else tokenize)
                normalized_dict = {k: normalize_unicode(v) for k, v in active_dict.items()}
                start_sentence = (
                    find_sentence_by_candidates(available_tokens, normalized_dict, start_fn)
                    or find_sentence_by_candidates(
                        available_tokens,
                        {k: strip_parens(v) for k, v in normalized_dict.items()}, start_fn)
                )
                if not start_sentence:
                    if stop_event.wait(timeout=0.3):
                        break
                    continue

                click_remaining_tokens(driver, start_fn(start_sentence), stop_event)
                if stop_event.wait(timeout=0.3):
                    break
                continue

            prefix_tokens = [normalize_unicode(t) for t in prefix_tokens]
            tokenize_fn = tokenize_loose if is_prefix_punct_split(prefix_tokens) else tokenize

            normalized_dict = {k: normalize_unicode(v) for k, v in active_dict.items()}

            matches = find_matching_sentences(prefix_tokens, normalized_dict, tokenize_fn)
            working_dict = normalized_dict

            if not matches:
                working_dict = {k: strip_parens(v) for k, v in normalized_dict.items()}
                matches = find_matching_sentences(prefix_tokens, working_dict, tokenize_fn)

            sentence = None
            subseq_end = -1

            if len(matches) == 1:
                sentence = matches[0]
            elif len(matches) > 1:
                available_tokens = [normalize_unicode(t) for t in get_available_tokens(driver)]
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

            if not sentence:
                print(f"[문장 리콜] 매칭 실패: {prefix_tokens}")
                if stop_event.wait(timeout=0.3):
                    break
                continue

            all_tokens = tokenize_fn(sentence)
            if subseq_end >= 0:
                remaining_tokens = all_tokens[subseq_end + 1:]
            else:
                remaining_tokens = all_tokens[len(prefix_tokens):]

            if any('(' in t or ')' in t for t in remaining_tokens):
                stripped_dict = {k: strip_parens(v) for k, v in normalized_dict.items()}
                alt = find_matching_sentences(prefix_tokens, stripped_dict, tokenize_fn)
                alt_sentence = alt[0] if len(alt) == 1 else None
                if alt_sentence is None:
                    alt_cands = []
                    for s_alt in stripped_dict.values():
                        s_tok = tokenize_fn(s_alt)
                        end_alt = find_subsequence_end(prefix_tokens, s_tok)
                        if end_alt >= 0:
                            alt_cands.append((s_alt, end_alt, s_tok))
                    if alt_cands:
                        alt_cands.sort(key=lambda c: len(c[2]))
                        alt_sentence, subseq_end, all_tokens = alt_cands[0]
                        remaining_tokens = all_tokens[subseq_end + 1:]
                        sentence = alt_sentence
                else:
                    sentence = alt_sentence
                    all_tokens = tokenize_fn(sentence)
                    remaining_tokens = all_tokens[len(prefix_tokens):]
                    subseq_end = -1

            click_remaining_tokens(driver, remaining_tokens, stop_event)

            if stop_event.is_set():
                break

            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
            if stop_event.wait(timeout=0.7):
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
