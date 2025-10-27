import threading
from pynput import keyboard
from selenium import webdriver
from pynput.keyboard import GlobalHotKeys
from selenium.webdriver.chrome.options import Options
import atexit
import Spell  
import Recall
import Memorize

URL = 'https://www.classcard.net/Login' # 클카 로그인 페이지

driver = None
answer_dict = None
automation_thread = None
stop_event = None
automation_lock = threading.Lock()

def initialize_browser():
    print("웹 드라이버를 설정하고 브라우저를 시작합니다...")
    chrome_options = Options()

    # ================= 자동화 탐지 우회 ====================================
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    chrome_options.add_argument(f'user-agent={user_agent}')
    # =====================================================================
    
    try:
        driver_instance = webdriver.Chrome(options=chrome_options)
        driver_instance.get(URL)
        return driver_instance
    except Exception as e:
        print(f"드라이버 시작 중 오류 발생: {e}")
        print("ChromeDriver가 설치되어 있고, 버전이 Chrome 브라우저와 맞는지 확인하세요.")
        return None

def start_automation_spell():
    global automation_thread, stop_event, driver, answer_dict
    
    if driver is None or answer_dict is None:
        print("\n[!] 드라이버 또는 정답 딕셔너리가 준비되지 않았습니다.")
 
        return
    
    with automation_lock:
        if automation_thread is None or not automation_thread.is_alive():
            stop_event = threading.Event()
            automation_thread = threading.Thread(
                target=Spell.run_automation_loop, 
                args=(driver, answer_dict, stop_event)
            )
            automation_thread.start()
        else:
            print("\n[X] 자동화가 이미 실행 중입니다.")

def start_automation_recall():
    global automation_thread, stop_event, driver, answer_dict
    
    if driver is None or answer_dict is None:
        print("\n[!] 드라이버 또는 정답 딕셔너리가 준비되지 않았습니다.")
        return
    
    with automation_lock:
        if automation_thread is None or not automation_thread.is_alive():
            stop_event = threading.Event()
            automation_thread = threading.Thread(
                target=Recall.run_automation_loop, 
                args=(driver, answer_dict, stop_event)
            )
            automation_thread.start()
        else:
            print("\n[Y] 자동화가 이미 실행 중입니다.")

def start_automation_memorize():
    global automation_thread, stop_event, driver, answer_dict
    if driver is None or answer_dict is None:
        print("\n[!] 드라이버 또는 정답 딕셔너리가 준비되지 않았습니다.")
        return
    with automation_lock:
        if automation_thread is None or not automation_thread.is_alive():
            stop_event = threading.Event()
            automation_thread = threading.Thread(
                target=Memorize.run_automation_loop, 
                args=(driver, answer_dict, stop_event)
            )
            automation_thread.start()
        else:
            print("\n[I] 자동화가 이미 실행 중입니다.")

def stop_automation():
    global automation_thread, stop_event
    
    with automation_lock:
        if automation_thread and automation_thread.is_alive():
            if stop_event:
                print("\n[ctrl + E] 키 입력: 자동화를 중지합니다...")
                stop_event.set()
            automation_thread = None 
        else:
            print("\n[ctrl + E] 키 입력: 현재 실행 중인 자동화가 없습니다.")

def cleanup_on_exit():
    global driver
    if driver:
        print("\n프로그램 종료... 브라우저를 닫습니다.")
        driver.quit()

def on_esc_release(key):
    global hotkey_listener
    if key == keyboard.Key.esc:
        print("\n[Esc] 키 입력: 프로그램을 종료합니다...")
        stop_automation()
        if hotkey_listener:
            hotkey_listener.stop()
        return False

if __name__ == "__main__":
    atexit.register(cleanup_on_exit)

    answer_dict = Spell.create_answer_dict()
    
    if answer_dict:
        driver = initialize_browser()
    
    if driver and answer_dict:
        print("\n--- 클래스카드 스펠 자동화 컨트롤러 ---")
        print("브라우저가 열렸습니다. 로그인 후 스펠 학습 페이지로 이동하세요.")
        print("   [Ctrl + I] 키 : 암기 자동화 시작")
        print("   [Ctrl + Y] 키 : 리콜 자동화 시작")
        print("\n   [ctrl + X] 키 : 스펠 자동화 시작")
        print("   [Ctrl + E] 키 : 자동화 멈추기")
        print("   [Esc] 키      : 프로그램 전체 종료 (브라우저 닫힘)")
        print("--------------------------------------------------")

        hotkey_listener = GlobalHotKeys({
            '<ctrl>+x': start_automation_spell,
            '<ctrl>+y': start_automation_recall,
            '<ctrl>+i': start_automation_memorize,
            '<ctrl>+e': stop_automation,
        })
        
        esc_listener = keyboard.Listener(
            on_release=on_esc_release
        )
        
        hotkey_listener.start()
        esc_listener.start()
        
        esc_listener.join()

    else:
        print("\n[오류] 정답 파일(data.json) 또는 웹 드라이버 문제로 프로그램을 시작할 수 없습니다.")

    print("프로그램이 종료되었습니다.")