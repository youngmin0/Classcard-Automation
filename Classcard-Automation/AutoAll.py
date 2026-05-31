import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchWindowException

import HtmlParser
import Spell
import Memorize
import MemorizeSentence
import Recall
import RecallSentence


SET_ITEM_SELECTOR = ".set-item"
SET_NAME_LINK_SELECTOR = ".set-item a.set-name-a"
MEMORIZE_BTN_SELECTOR = '.btn-summary[onclick*="/Memorize/"]'
RECALL_BTN_SELECTOR = '.btn-summary[onclick*="/Recall/"]'
VIEW_TYPE_LABEL_SELECTOR = '.str_view_type'
VIEW_TYPE_TOGGLE_SELECTOR = 'a[data-toggle="dropdown"] .str_view_type'
START_LEARNING_BTN_SELECTOR = '.btn-opt-start'
FULL_CARDS_DATA_IDX = "6"
FULL_CARDS_LABEL = "전체 카드 학습"


def is_sentence_set(set_name: str) -> bool:
    return set_name.strip().endswith('(예문)')


def get_set_name(driver, element) -> str:
    """<a> 태그의 첫 텍스트 노드만 추출 ("18 카드" 같은 span 텍스트 제외)."""
    try:
        name = driver.execute_script(
            "var n = arguments[0].firstChild; return n ? n.textContent : '';",
            element
        )
        return (name or '').strip()
    except Exception:
        return (element.text or '').split('\n')[0].strip()


def get_set_items(driver):
    try:
        anchors = driver.find_elements(By.CSS_SELECTOR, SET_NAME_LINK_SELECTOR)
        result = []
        for a in anchors:
            try:
                idx = a.get_attribute('data-idx')
                name = get_set_name(driver, a)
                result.append({'element': a, 'idx': idx, 'name': name})
            except Exception:
                continue
        return result
    except NoSuchWindowException:
        raise
    except Exception as e:
        print(f"[전체] set 목록 읽기 오류: {e}")
        return []


def wait_for_set_detail(driver, timeout=10) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.btn-summary'))
        )
        return True
    except TimeoutException:
        return False


def wait_for_set_list(driver, timeout=10) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SET_ITEM_SELECTOR))
        )
        return True
    except TimeoutException:
        return False


def is_mode_completed(driver, btn_selector) -> bool:
    try:
        btn = driver.find_element(By.CSS_SELECTOR, btn_selector)
        return len(btn.find_elements(By.CSS_SELECTOR, '.check-icon')) > 0
    except Exception:
        return False


def is_full_cards_mode(driver) -> bool:
    """현재 active 옵션이 '전체 카드 학습'(data-idx=6)인지."""
    try:
        active = driver.find_element(By.CSS_SELECTOR, '.sel-show-type.active')
        return active.get_attribute('data-idx') == FULL_CARDS_DATA_IDX
    except Exception:
        return False


def ensure_full_cards_mode(driver, stop_event) -> bool:
    """학습 구간 드롭다운을 '전체 카드 학습'으로 설정."""
    if is_full_cards_mode(driver):
        return True

    try:
        toggle_label = driver.find_element(By.CSS_SELECTOR, VIEW_TYPE_TOGGLE_SELECTOR)
        toggle_a = toggle_label.find_element(By.XPATH, "./ancestor::a[@data-toggle='dropdown']")
        driver.execute_script("arguments[0].click();", toggle_a)
    except Exception as e:
        print(f"[전체] 학습구간 드롭다운을 찾지 못했습니다: {e}")
        return False

    if stop_event.wait(timeout=0.5):
        return False

    option = None
    try:
        option = driver.find_element(By.CSS_SELECTOR, f'.sel-show-type[data-idx="{FULL_CARDS_DATA_IDX}"]')
    except Exception:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, '.sel-show-type'):
                if el.text.strip() == FULL_CARDS_LABEL:
                    option = el
                    break
        except Exception:
            pass

    if option is None:
        print(f"[전체] '{FULL_CARDS_LABEL}' 옵션을 찾지 못했습니다.")
        return False

    try:
        driver.execute_script("arguments[0].click();", option)
    except Exception as e:
        print(f"[전체] '{FULL_CARDS_LABEL}' 옵션 클릭 오류: {e}")
        return False

    try:
        WebDriverWait(driver, 5).until(lambda d: is_full_cards_mode(d))
        print(f"[전체] 학습구간 → '{FULL_CARDS_LABEL}'")
        return True
    except TimeoutException:
        print(f"[전체] 학습구간 변경 확인 실패.")
        return False


def click_start_learning(driver, stop_event) -> bool:
    """모드 진입 후 나오는 '암기학습/리콜학습 (N구간)' 시작 버튼을 클릭."""
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, START_LEARNING_BTN_SELECTOR))
        )
    except TimeoutException:
        print(f"[전체] 시작 버튼({START_LEARNING_BTN_SELECTOR})을 찾지 못했습니다.")
        return False

    if stop_event.is_set():
        return False

    try:
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)
        return True
    except Exception as e:
        print(f"[전체] 시작 버튼 클릭 오류: {e}")
        return False


def click_mode_button(driver, btn_selector) -> bool:
    try:
        btn = driver.find_element(By.CSS_SELECTOR, btn_selector)
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)
        return True
    except Exception as e:
        print(f"[전체] 버튼 클릭 오류 ({btn_selector}): {e}")
        return False


def run_mode_isolated(driver, mode_fn, answer_dict, parent_stop_event):
    """모드 함수에는 sub-event를 넘겨서 모드 종료 시 호출하는 stop_event.set()이
    parent(전체 자동화)에 전파되지 않도록 격리. 단, parent가 set되면 sub로 전파."""
    mode_stop_event = threading.Event()

    def propagate():
        while True:
            if parent_stop_event.wait(timeout=0.3):
                mode_stop_event.set()
                return
            if mode_stop_event.is_set():
                return

    propagator = threading.Thread(target=propagate, daemon=True)
    propagator.start()

    try:
        mode_fn(driver, answer_dict, mode_stop_event)
    finally:
        mode_stop_event.set()


def run_full_automation_loop(driver, stop_event: threading.Event):
    print("[전체] 시작 (Ctrl+E로 중지)")

    if not wait_for_set_list(driver, timeout=3):
        print("[전체] .set-item을 찾을 수 없습니다. 단어장 목록 페이지에서 시작하세요.")
        return

    processed_idx_set = set()

    try:
        while not stop_event.is_set():
            sets = get_set_items(driver)
            if not sets:
                print("[전체] set 목록이 비어있습니다. 종료.")
                break

            target = None
            for s in reversed(sets):
                if s['idx'] and s['idx'] not in processed_idx_set:
                    target = s
                    break

            if target is None:
                print("[전체] 모든 set 처리 완료.")
                break

            sentence_mode = is_sentence_set(target['name'])
            print(f"\n[전체] [{'문장' if sentence_mode else '단어'}] {target['name']}")

            try:
                try:
                    target['element'].click()
                except Exception:
                    driver.execute_script("arguments[0].click();", target['element'])
            except Exception as e:
                print(f"[전체] set 클릭 실패: {e}")
                processed_idx_set.add(target['idx'])
                continue

            if not wait_for_set_detail(driver, timeout=10):
                print("[전체] set 상세 페이지 진입 실패. 다음 set로 이동.")
                processed_idx_set.add(target['idx'])
                try:
                    driver.back()
                    wait_for_set_list(driver, timeout=5)
                except Exception:
                    pass
                continue

            if stop_event.is_set():
                break

            memorize_done = is_mode_completed(driver, MEMORIZE_BTN_SELECTOR)
            recall_done = is_mode_completed(driver, RECALL_BTN_SELECTOR)
            if memorize_done and recall_done:
                print("[전체] 암기/리콜 모두 완료 — set 스킵")
                processed_idx_set.add(target['idx'])
                try:
                    driver.back()
                    wait_for_set_list(driver, timeout=10)
                except Exception:
                    pass
                continue

            ensure_full_cards_mode(driver, stop_event)

            if stop_event.is_set():
                break

            data = HtmlParser.get_data(driver)
            if not data:
                print("[전체] data.json 추출 실패. 다음 set로 이동.")
                processed_idx_set.add(target['idx'])
                try:
                    driver.back()
                    wait_for_set_list(driver, timeout=5)
                except Exception:
                    pass
                continue

            answer_dict = Spell.create_answer_dict()
            if not answer_dict:
                print("[전체] answer_dict 생성 실패. 다음 set로 이동.")
                processed_idx_set.add(target['idx'])
                try:
                    driver.back()
                    wait_for_set_list(driver, timeout=5)
                except Exception:
                    pass
                continue

            mode_steps = [
                ('암기', MEMORIZE_BTN_SELECTOR,
                 MemorizeSentence.run_automation_loop if sentence_mode else Memorize.run_automation_loop),
                ('리콜', RECALL_BTN_SELECTOR,
                 RecallSentence.run_automation_loop if sentence_mode else Recall.run_automation_loop),
            ]

            for mode_label, btn_selector, mode_fn in mode_steps:
                if stop_event.is_set():
                    break

                if is_mode_completed(driver, btn_selector):
                    print(f"[전체] {mode_label} 이미 완료 — 스킵.")
                    continue

                if not click_mode_button(driver, btn_selector):
                    print(f"[전체] {mode_label} 버튼 클릭 실패. 스킵.")
                    continue

                if stop_event.wait(timeout=1.5):
                    break

                if not click_start_learning(driver, stop_event):
                    print(f"[전체] {mode_label} 시작 버튼 클릭 실패. 스킵.")
                    continue

                if stop_event.wait(timeout=1.5):
                    break

                run_mode_isolated(driver, mode_fn, answer_dict, stop_event)

                if stop_event.is_set():
                    break

                if not wait_for_set_detail(driver, timeout=15):
                    print(f"[전체] {mode_label} 후 set 페이지 복귀 실패. 다음 set로 이동.")
                    break

            if stop_event.is_set():
                break

            processed_idx_set.add(target['idx'])

            try:
                driver.back()
            except Exception as e:
                print(f"[전체] driver.back() 오류: {e}")
                break

            if not wait_for_set_list(driver, timeout=10):
                print("[전체] 단어장 목록 페이지 복귀 실패. 종료.")
                break

            if stop_event.wait(timeout=1.0):
                break

    except NoSuchWindowException:
        if not stop_event.is_set():
            print("[전체] 브라우저 창이 닫혔습니다.")
    except Exception as e:
        if not stop_event.is_set():
            print(f"[전체] 오류: {e}")

    finally:
        print("[전체] 종료")
