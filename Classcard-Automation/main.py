import os
import threading
from dotenv import load_dotenv
from pynput import keyboard
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pynput.keyboard import GlobalHotKeys
from selenium.webdriver.chrome.options import Options
import atexit
import Spell
import Recall
import Memorize
import MemorizeSentence
import RecallSentence
import HtmlParser
import AutoAll
import Test
import TestSentence
import Matching
import Scramble

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

URL = 'https://www.classcard.net/Login'

# 다계정 병렬 시 크롬 창 크기/배치.
# ⚠ 창(뷰포트)이 좁으면 클래스카드가 'page-small' 모바일 레이아웃으로 바뀌어
#   스크램블 타일을 일부만 보여주는 등 자동화가 깨진다. 그래서 데스크톱 레이아웃이 유지되도록
#   '충분히 큰' 크기를 강제하고, 창은 계단식으로 살짝 어긋나게 겹쳐 띄운다.
#   (포커스가 없어도/창이 겹쳐도 백그라운드에서 정상 동작함)
WIN_W = 1280
WIN_H = 900
WIN_CASCADE = 48   # 계정마다 어긋나게 띄울 간격(px)
WIN_CASCADE_WRAP = 8  # 이 개수마다 위치를 처음으로 되돌림(화면 밖으로 너무 밀리지 않게)

# 테스트 '이탈 감지' 우회: 탭/창 포커스를 잃어도 페이지가 항상 '보이고 포커스된' 상태로 보이게 위장.
# (Page Visibility API 고정 + visibilitychange/blur 이벤트를 캡처 단계에서 차단)
ANTI_BLUR_JS = r'''
(function(){
  try {
    Object.defineProperty(document, 'hidden', {configurable:true, get:function(){return false;}});
    Object.defineProperty(document, 'visibilityState', {configurable:true, get:function(){return 'visible';}});
    Object.defineProperty(document, 'webkitHidden', {configurable:true, get:function(){return false;}});
    Object.defineProperty(document, 'webkitVisibilityState', {configurable:true, get:function(){return 'visible';}});
  } catch(e){}
  try { document.hasFocus = function(){ return true; }; } catch(e){}
  function blocker(e){
    var t = e.type;
    if (t === 'visibilitychange' || t === 'webkitvisibilitychange' ||
        t === 'mozvisibilitychange' || t === 'msvisibilitychange' || t === 'pagehide') {
      e.stopImmediatePropagation(); return;
    }
    if ((t === 'blur' || t === 'focusout') && (e.target === window || e.target === document)) {
      e.stopImmediatePropagation();
    }
  }
  var evts = ['visibilitychange','webkitvisibilitychange','mozvisibilitychange',
              'msvisibilitychange','pagehide','blur','focusout'];
  evts.forEach(function(ev){
    window.addEventListener(ev, blocker, true);
    document.addEventListener(ev, blocker, true);
  });
  try { window.onblur = null; } catch(e){}
})();
'''

# 문장 리콜 정답 캡처: recall_sentence.min.js 는 정답을 console.log('arr_front', ...) 로 출력한다.
# 페이지 스크립트보다 먼저 console.log 를 후킹해 정답 문장을 window.__cc_answers 에 모은다.
# (리콜은 완성 정답이 DOM/전역에 없고, 틀린 단어는 그대로 박혀서 brute-force 불가 → 이 방법이 유일하게 안전)
ANSWER_CAPTURE_JS = r'''
(function(){
  try {
    if (window.__ccAnswerHook) return;
    window.__ccAnswerHook = true;
    window.__cc_answers = [];
    var orig = console.log;
    console.log = function(){
      try {
        if (arguments[0] === 'arr_front') {
          var s = null;
          for (var i = 1; i < arguments.length; i++) {
            if (typeof arguments[i] === 'string' && arguments[i].trim()) { s = arguments[i].trim(); break; }
          }
          if (!s && Array.isArray(arguments[1])) s = arguments[1].join(' ');
          if (s) window.__cc_answers.push(s);
        }
      } catch (e) {}
      return orig.apply(console, arguments);
    };
  } catch (e) {}
})();
'''


class Account:
    """계정 1개 = 크롬 1개. 계정마다 독립된 driver / answer_dict / 자동화 스레드를 가진다."""
    def __init__(self, user_id, user_pw):
        self.user_id = user_id
        self.user_pw = user_pw
        self.driver = None
        self.answer_dict = None
        self.thread = None
        self.stop_event = None
        self.lock = threading.Lock()

    @property
    def tag(self):
        return f"[{self.user_id}]"


accounts = []  # type: list[Account]
exit_event = threading.Event()


def parse_accounts():
    """.env에서 여러 계정을 읽는다.
    - CLASSCARD_ID / CLASSCARD_PW 에 쉼표(,)로 여러 개를 적을 수 있다.
    - 추가로 CLASSCARD_ID_2/PW_2, _3 ... 번호 형식도 인식한다.
    """
    pairs = []

    ids = [s.strip() for s in (os.getenv("CLASSCARD_ID") or "").split(",") if s.strip()]
    pws = [s.strip() for s in (os.getenv("CLASSCARD_PW") or "").split(",") if s.strip()]
    for uid, upw in zip(ids, pws):
        pairs.append((uid, upw))
    if len(ids) != len(pws):
        print(f"[!] .env CLASSCARD_ID({len(ids)}개)와 CLASSCARD_PW({len(pws)}개) 개수가 다릅니다. "
              f"맞는 개수({min(len(ids), len(pws))}개)만 사용합니다.")

    n = 2
    while True:
        uid = os.getenv(f"CLASSCARD_ID_{n}")
        upw = os.getenv(f"CLASSCARD_PW_{n}")
        if not uid or not upw:
            break
        pairs.append((uid.strip(), upw.strip()))
        n += 1

    # 중복 제거(순서 유지)
    seen = set()
    result = []
    for uid, upw in pairs:
        if uid in seen:
            continue
        seen.add(uid)
        result.append(Account(uid, upw))
    return result


def initialize_browser(account, position_index):
    print(f"{account.tag} 웹 드라이버를 설정하고 브라우저를 시작합니다...")
    chrome_options = Options()

    # ================= 자동화 탐지 우회 ====================================
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    chrome_options.add_argument(f'user-agent={user_agent}')
    # =====================================================================

    # 데스크톱 레이아웃 유지를 위해 큰 크기로 띄우고, 계정마다 계단식으로 살짝 겹쳐 배치
    step = position_index % WIN_CASCADE_WRAP
    pos_x = step * WIN_CASCADE
    pos_y = step * WIN_CASCADE
    chrome_options.add_argument(f"--window-size={WIN_W},{WIN_H}")
    chrome_options.add_argument(f"--window-position={pos_x},{pos_y}")

    try:
        driver_instance = webdriver.Chrome(options=chrome_options)
        # 모든 새 문서에 '이탈 감지 우회' + '리콜 정답 캡처' 스크립트를 사전 주입
        # (페이지 스크립트보다 먼저 실행되어야 함)
        try:
            driver_instance.execute_cdp_cmd(
                'Page.addScriptToEvaluateOnNewDocument', {'source': ANTI_BLUR_JS}
            )
            driver_instance.execute_cdp_cmd(
                'Page.addScriptToEvaluateOnNewDocument', {'source': ANSWER_CAPTURE_JS}
            )
        except Exception as e:
            print(f"{account.tag} [!] 사전 주입 실패(무시하고 진행): {e}")
        driver_instance.get(URL)
        account.driver = driver_instance
        auto_login(account)
        return driver_instance
    except Exception as e:
        print(f"{account.tag} 드라이버 시작 중 오류 발생: {e}")
        print("ChromeDriver가 설치되어 있고, 버전이 Chrome 브라우저와 맞는지 확인하세요.")
        return None


def auto_login(account):
    driver_instance = account.driver
    user_id = account.user_id
    user_pw = account.user_pw
    if not user_id or not user_pw:
        print(f"{account.tag} [!] 아이디/비밀번호가 없습니다. 수동 로그인하세요.")
        return

    try:
        wait = WebDriverWait(driver_instance, 10)

        id_input = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[type='text'][name*='id' i], input[type='text'][name*='Id' i], input#userId, input[placeholder*='아이디']")
        ))
        pw_input = driver_instance.find_element(By.CSS_SELECTOR, "input[type='password']")

        driver_instance.execute_script(
            "arguments[0].value = arguments[1];"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            id_input, user_id
        )
        driver_instance.execute_script(
            "arguments[0].value = arguments[1];"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            pw_input, user_pw
        )

        try:
            alert = driver_instance.switch_to.alert
            alert.dismiss()
        except Exception:
            pass

        login_btn = driver_instance.find_element(
            By.CSS_SELECTOR, "a.btn-login"
        )
        login_btn.click()

        try:
            alert = driver_instance.switch_to.alert
            alert.dismiss()
        except Exception:
            pass

        wait.until(EC.url_changes(URL))
        print(f"{account.tag} [O] 로그인 성공")

    except Exception as e:
        print(f"{account.tag} [!] 자동 로그인 실패: {e}")
        print(f"{account.tag}     수동으로 로그인해 주세요.")


def ensure_answer_dict(account):
    """answer_dict가 없으면 현재 페이지에서 단어장을 파싱해 계정 전용 딕셔너리를 만든다."""
    if account.answer_dict is not None:
        return account.answer_dict
    try:
        data = HtmlParser.get_data(account.driver, output_path=None)
        account.answer_dict = Spell.dict_from_cards(data)
    except Exception as e:
        print(f"{account.tag} 단어장 자동 추출 실패: {e}")
        account.answer_dict = None
    return account.answer_dict


def start_one(account, module_func, needs_dict):
    """한 계정에서 자동화 스레드를 시작."""
    if account.driver is None:
        return
    with account.lock:
        if account.thread and account.thread.is_alive():
            print(f"{account.tag} [X] 자동화가 이미 실행 중입니다.")
            return

        if needs_dict:
            if ensure_answer_dict(account) is None:
                print(f"{account.tag} [!] 단어장이 없습니다. 학습 페이지로 이동 후 Ctrl+M으로 가져오세요.")
                return

        account.stop_event = threading.Event()
        if needs_dict:
            args = (account.driver, account.answer_dict, account.stop_event)
        else:
            args = (account.driver, account.stop_event)
        account.thread = threading.Thread(target=module_func, args=args, daemon=True)
        account.thread.start()
        print(f"{account.tag} 자동화 시작")


def make_starter(module_func, needs_dict=True):
    """단축키 하나로 모든 계정에서 동시에 module_func를 시작하는 핸들러를 만든다."""
    def starter():
        for account in accounts:
            start_one(account, module_func, needs_dict)
    return starter


# 모든 계정에 fan-out 되는 시작 핸들러들
start_automation_spell = make_starter(Spell.run_automation_loop)
start_automation_recall = make_starter(Recall.run_automation_loop)
start_automation_memorize = make_starter(Memorize.run_automation_loop)
start_automation_memorize_sentence = make_starter(MemorizeSentence.run_automation_loop)
start_automation_recall_sentence = make_starter(RecallSentence.run_automation_loop)
start_automation_test = make_starter(Test.run_automation_loop)
start_automation_test_sentence = make_starter(TestSentence.run_automation_loop)
start_automation_matching = make_starter(Matching.run_automation_loop)
start_automation_scramble = make_starter(Scramble.run_automation_loop)
start_automation_all = make_starter(AutoAll.run_full_automation_loop, needs_dict=False)
start_automation_one_set = make_starter(AutoAll.run_single_set_loop, needs_dict=False)


def stop_automation():
    print("\n[Ctrl + E] 키 입력: 모든 계정 자동화를 중지합니다...")
    any_running = False
    for account in accounts:
        with account.lock:
            if account.thread and account.thread.is_alive():
                any_running = True
                if account.stop_event:
                    account.stop_event.set()
                account.thread = None
    if not any_running:
        print("    현재 실행 중인 자동화가 없습니다.")


def html_parse():
    """모든 계정에서 각자의 현재 페이지 단어장을 가져와 계정별 answer_dict 갱신."""
    print("\n[Ctrl + M] 키 입력: 모든 계정의 단어장을 가져옵니다...")
    for account in accounts:
        if account.driver is None:
            continue
        try:
            data = HtmlParser.get_data(account.driver, output_path=None)
            new_dict = Spell.dict_from_cards(data)
            if new_dict:
                account.answer_dict = new_dict
                print(f"{account.tag} 단어장 갱신 완료 ({len(new_dict)}개)")
            else:
                print(f"{account.tag} 단어장 추출 실패 (학습 페이지가 맞는지 확인)")
        except Exception as e:
            print(f"{account.tag} 단어장 추출 오류: {e}")


def cleanup_on_exit():
    for account in accounts:
        if account.driver:
            try:
                account.driver.quit()
            except Exception:
                pass
    if accounts:
        print("\n프로그램 종료... 브라우저를 닫습니다.")


def exit_program():
    print("\n[Ctrl + Esc] 키 입력: 프로그램을 종료합니다...")
    stop_automation()
    exit_event.set()


if __name__ == "__main__":
    atexit.register(cleanup_on_exit)

    accounts = parse_accounts()

    if not accounts:
        print("[오류] .env에 계정이 없습니다. CLASSCARD_ID / CLASSCARD_PW를 설정하세요.")
        print('       예) CLASSCARD_ID=acc1,acc2   CLASSCARD_PW=pw1,pw2')
    else:
        print(f"총 {len(accounts)}개 계정으로 시작합니다: {', '.join(a.user_id for a in accounts)}")
        for i, account in enumerate(accounts):
            initialize_browser(account, i)

    launched = [a for a in accounts if a.driver is not None]

    if launched:
        print("\n--- 클래스카드 다계정 병렬 자동화 컨트롤러 ---")
        print(f"브라우저 {len(launched)}개가 열렸습니다. 각 계정 창에서 학습 페이지로 이동하세요.")
        print("단축키 한 번이면 '모든 계정'에서 동시에 동작합니다.")
        print("\n   [Ctrl + I] 키 : 암기 자동화 시작")
        print("   [Ctrl + Y] 키 : 리콜 자동화 시작")
        print("   [Ctrl + X] 키 : 스펠 자동화 시작")
        print("   [Ctrl + B] 키 : 문장 암기 자동화 시작")
        print("   [Ctrl + Q] 키 : 문장 리콜 자동화 시작")
        print("   [Ctrl + Alt + G] 키 : 단어 테스트 자동화 시작")
        print("   [Ctrl + Alt + H] 키 : 문장 테스트 자동화 시작")
        print("   [Ctrl + Alt + J] 키 : 단어 매칭 자동화 시작")
        print("   [Ctrl + Alt + K] 키 : 문장 스크램블 자동화 시작")
        print("   [Ctrl + A] 키 : 전체 자동화 시작 (단어장 목록 페이지에서)")
        print("   [Ctrl + Alt + S] 키 : 현재 셋홈 한 세트 전체 자동화 시작")
        print("   [Ctrl + E] 키 : 자동화 멈추기 (전체 계정)")
        print("   [Ctrl + M] 키 : 단어장 가져오기 (전체 계정)")
        print("   [Ctrl + Esc] 키 : 프로그램 전체 종료 (브라우저 닫힘)")
        print("--------------------------------------------------")

        hotkey_listener = GlobalHotKeys({
            '<ctrl>+x': start_automation_spell,
            '<ctrl>+y': start_automation_recall,
            '<ctrl>+i': start_automation_memorize,
            '<ctrl>+b': start_automation_memorize_sentence,
            '<ctrl>+q': start_automation_recall_sentence,
            '<ctrl>+<alt>+g': start_automation_test,
            '<ctrl>+<alt>+h': start_automation_test_sentence,
            '<ctrl>+<alt>+j': start_automation_matching,
            '<ctrl>+<alt>+k': start_automation_scramble,
            '<ctrl>+a': start_automation_all,
            '<ctrl>+<alt>+s': start_automation_one_set,
            '<ctrl>+e': stop_automation,
            '<ctrl>+m': html_parse,
            '<ctrl>+<esc>': exit_program,
        })

        hotkey_listener.start()
        exit_event.wait()
        hotkey_listener.stop()

    else:
        print("\n[오류] 웹 드라이버 문제로 프로그램을 시작할 수 없습니다.")

    print("프로그램이 종료되었습니다.")
