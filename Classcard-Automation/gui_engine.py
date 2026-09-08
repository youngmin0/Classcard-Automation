"""GUI와 자동화 엔진(main.py)을 잇는 컨트롤러.

- 자동화 로직은 전부 기존 모듈(main.py / AutoAll.py / Spell.py ...)을 그대로 재사용한다.
- GUI는 이 모듈만 호출하고, 실제 동작/단축키/다계정 병렬 실행은 기존 코드와 동일하다.
"""

import json
import os
import sys
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime

import main as core

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
SETTINGS_PATH = os.path.join(BASE_DIR, "gui_settings.json")
ENV_PATH = os.path.join(BASE_DIR, ".env")


# ────────────────────────────────────────────────────────────────────────────
# 학습 모드 정의 (CLI 단축키와 1:1로 대응)
# ────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Mode:
    key: str
    label: str
    icon: str
    desc: str
    hotkey: str
    needs_dict: bool
    module: str
    func: str

    def callable(self):
        return getattr(getattr(core, self.module), self.func)


MODES = [
    Mode("all", "전체 자동화", "⚡",
         "단어장 목록 페이지에서 맨 아래 set부터 순서대로 전 과정을 자동 수행합니다.",
         "Ctrl + A", False, "AutoAll", "run_full_automation_loop"),
    Mode("one_set", "한 세트 자동화", "◎",
         "열어둔 셋홈(set 상세) 페이지 한 세트만 전체 모드로 수행합니다.",
         "Ctrl + Alt + S", False, "AutoAll", "run_single_set_loop"),
    Mode("memorize", "암기", "📖",
         "단어 암기 학습을 자동으로 진행합니다.",
         "Ctrl + I", True, "Memorize", "run_automation_loop"),
    Mode("recall", "리콜", "🔁",
         "단어 리콜 학습을 자동으로 진행합니다.",
         "Ctrl + Y", True, "Recall", "run_automation_loop"),
    Mode("spell", "스펠", "⌨",
         "정답 목록을 기반으로 스펠 학습을 자동 타이핑합니다.",
         "Ctrl + X", True, "Spell", "run_automation_loop"),
    Mode("memorize_sentence", "문장 암기", "📗",
         "문장 세트의 암기 학습을 자동으로 진행합니다.",
         "Ctrl + B", True, "MemorizeSentence", "run_automation_loop"),
    Mode("recall_sentence", "문장 리콜", "📘",
         "문장 세트의 리콜 학습을 자동으로 진행합니다.",
         "Ctrl + Q", True, "RecallSentence", "run_automation_loop"),
    Mode("test", "단어 테스트", "📝",
         "단어 객관식 테스트를 자동으로 풉니다. (70점 초과 보장, 백그라운드 가능)",
         "Ctrl + Alt + G", True, "Test", "run_automation_loop"),
    Mode("test_sentence", "문장 테스트", "🧾",
         "문장 어순 배열 테스트를 자동으로 풉니다. (90점 패스 기준, 백그라운드 가능)",
         "Ctrl + Alt + H", True, "TestSentence", "run_automation_loop"),
    Mode("matching", "단어 매칭", "🃏",
         "영어↔한국어 카드 매칭 게임을 자동으로 풉니다. (1000~2000점)",
         "Ctrl + Alt + J", True, "Matching", "run_automation_loop"),
    Mode("scramble", "문장 스크램블", "🧩",
         "문장 어순 배열 게임을 자동으로 풉니다. (4000~5000점)",
         "Ctrl + Alt + K", True, "Scramble", "run_automation_loop"),
]

MODE_BY_KEY = {m.key: m for m in MODES}

# GUI 버튼 ↔ CLI 전역 단축키 매핑
HOTKEY_MAP = {
    '<ctrl>+a': "all",
    '<ctrl>+<alt>+s': "one_set",
    '<ctrl>+i': "memorize",
    '<ctrl>+y': "recall",
    '<ctrl>+x': "spell",
    '<ctrl>+b': "memorize_sentence",
    '<ctrl>+q': "recall_sentence",
    '<ctrl>+<alt>+g': "test",
    '<ctrl>+<alt>+h': "test_sentence",
    '<ctrl>+<alt>+j': "matching",
    '<ctrl>+<alt>+k': "scramble",
}


# ────────────────────────────────────────────────────────────────────────────
# 로그 (stdout/stderr를 가로채 GUI + 파일로 동시에 남긴다)
# ────────────────────────────────────────────────────────────────────────────
class LogBus:
    def __init__(self):
        self._listeners = []
        self._lock = threading.Lock()
        self._buffer = []
        self._installed = False
        self._orig_stdout = None
        self._orig_stderr = None
        os.makedirs(LOG_DIR, exist_ok=True)

    # -- 구독 ---------------------------------------------------------------
    def subscribe(self, callback):
        with self._lock:
            self._listeners.append(callback)

    def recent(self, limit=500):
        with self._lock:
            return list(self._buffer[-limit:])

    # -- 기록 ---------------------------------------------------------------
    def log(self, text, level="INFO"):
        stamp = datetime.now().strftime("%H:%M:%S")
        for raw_line in str(text).splitlines() or [""]:
            line = f"[{stamp}] {raw_line}" if raw_line.strip() else ""
            if not line:
                continue
            with self._lock:
                self._buffer.append(line)
                if len(self._buffer) > 5000:
                    del self._buffer[:1000]
                listeners = list(self._listeners)
            self._write_file(line)
            for cb in listeners:
                try:
                    cb(line)
                except Exception:
                    pass

    def _write_file(self, line):
        try:
            path = os.path.join(LOG_DIR, datetime.now().strftime("%Y-%m-%d") + ".log")
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def log_path(self, date_str):
        return os.path.join(LOG_DIR, f"{date_str}.log")

    def read_day(self, date_str):
        path = self.log_path(date_str)
        if not os.path.exists(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"로그 파일을 읽지 못했습니다: {e}"

    def clear_day(self, date_str):
        path = self.log_path(date_str)
        try:
            if os.path.exists(path):
                os.remove(path)
            if date_str == datetime.now().strftime("%Y-%m-%d"):
                with self._lock:
                    self._buffer.clear()
            return True
        except Exception:
            return False

    # -- stdout/stderr 가로채기 ---------------------------------------------
    def install(self):
        if self._installed:
            return
        self._installed = True
        self._orig_stdout, self._orig_stderr = sys.stdout, sys.stderr
        sys.stdout = _Tee(self._orig_stdout, self)
        sys.stderr = _Tee(self._orig_stderr, self)

    def uninstall(self):
        if not self._installed:
            return
        sys.stdout, sys.stderr = self._orig_stdout, self._orig_stderr
        self._installed = False


class _Tee:
    """print()를 원래 콘솔과 GUI 로그 양쪽으로 보낸다. (pythonw처럼 콘솔이 없어도 안전)"""

    def __init__(self, stream, bus):
        self._stream = stream
        self._bus = bus
        self._pending = ""

    def write(self, data):
        if self._stream is not None:
            try:
                self._stream.write(data)
            except Exception:
                pass
        self._pending += data
        while "\n" in self._pending:
            line, self._pending = self._pending.split("\n", 1)
            if line.strip():
                self._bus.log(line)
        return len(data)

    def flush(self):
        if self._stream is not None:
            try:
                self._stream.flush()
            except Exception:
                pass

    def isatty(self):
        return False


LOG = LogBus()


# ────────────────────────────────────────────────────────────────────────────
# 설정
# ────────────────────────────────────────────────────────────────────────────
def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@dataclass
class Settings:
    auto_login: bool = True
    anti_blur: bool = True
    cascade: bool = True
    keep_browser: bool = True         # 자동화 종료 후에도 브라우저 유지
    hotkeys: bool = True              # 전역 단축키 사용
    start_delay: int = 0              # 시작 지연(초)
    account_gap: int = 0              # 계정별 실행 간격(초)
    window_w: int = 1280
    window_h: int = 900
    chrome_binary: str = ""
    extra_args: str = ""
    schedule_enabled: bool = False
    schedule_time: str = "00:00:00"
    selected_mode: str = "all"

    @classmethod
    def load(cls, path=SETTINGS_PATH, fallback=None):
        """path의 설정을 읽는다. 없으면 fallback(예전 공용 설정)을 한 번 물려받는다."""
        data = _read_json(path)
        if data is None and fallback:
            data = _read_json(fallback)
        known = {k: v for k, v in (data or {}).items() if k in cls.__dataclass_fields__}
        settings = cls(**known)
        settings.path = path
        return settings

    def save(self, path=None):
        path = path or getattr(self, "path", SETTINGS_PATH)
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            LOG.log(f"[!] 설정 저장 실패: {e}")
            return False


# ────────────────────────────────────────────────────────────────────────────
# 엔진
# ────────────────────────────────────────────────────────────────────────────
STATE_IDLE = "대기"
STATE_READY = "준비됨"
STATE_RUNNING = "실행 중"
STATE_DONE = "완료"
STATE_ERROR = "오류"


class Engine:
    """계정 목록과 자동화 스레드를 관리한다. (GUI 프레임워크에 의존하지 않음)"""

    def __init__(self, on_change=None, profile_dir=None, user=None):
        # 로그인한 사용자마다 설정/계정 목록을 따로 보관한다.
        # (로그인 없이 쓰던 예전 설정은 profile_dir이 없을 때 그대로 사용)
        self.user = user
        self.profile_dir = profile_dir or BASE_DIR
        try:
            os.makedirs(self.profile_dir, exist_ok=True)
        except Exception:
            self.profile_dir = BASE_DIR
        self.settings_path = os.path.join(self.profile_dir, "gui_settings.json")
        self.accounts_path = os.path.join(self.profile_dir, "accounts.json")
        self.settings = Settings.load(self.settings_path,
                                      fallback=SETTINGS_PATH if profile_dir else None)
        self.accounts = []
        self._on_change = on_change or (lambda: None)
        self._monitor_stop = threading.Event()
        self._monitor = None
        self._hotkey_listener = None
        # main.py의 전역 리스트와 같은 객체를 공유해서, GUI/단축키 어느 쪽으로 시작하든
        # 같은 계정 목록을 대상으로 동작하게 만든다.
        core.accounts = self.accounts

    # -- 계정 저장소(사용자 프로필) -----------------------------------------
    def load_profile_accounts(self):
        """로그인한 사용자의 계정 목록(accounts.json)을 불러온다."""
        data = _read_json(self.accounts_path)
        if not isinstance(data, list):
            return 0
        added = 0
        for item in data:
            if isinstance(item, dict) and self.add_account(item.get("id"), item.get("pw"),
                                                           silent=True):
                added += 1
        if added:
            LOG.log(f"저장된 계정 {added}개를 불러왔습니다.")
            self._changed()
        return added

    def save_profile_accounts(self):
        try:
            os.makedirs(os.path.dirname(self.accounts_path) or ".", exist_ok=True)
            with open(self.accounts_path, "w", encoding="utf-8") as f:
                json.dump([{"id": a.user_id, "pw": a.user_pw or ""} for a in self.accounts],
                          f, ensure_ascii=False, indent=2)
            if os.name == "posix":
                os.chmod(self.accounts_path, 0o600)
            return True
        except Exception as e:
            LOG.log(f"[!] 계정 목록 저장 실패: {e}")
            return False

    def set_password(self, account, password):
        account.user_pw = password or ""
        self.save_profile_accounts()
        LOG.log(f"{account.tag} 비밀번호를 변경했습니다.")

    # -- 계정 ---------------------------------------------------------------
    def load_env_accounts(self):
        """`.env`의 CLASSCARD_ID/PW를 읽어 계정 목록에 추가한다."""
        try:
            from dotenv import load_dotenv
            load_dotenv(ENV_PATH, override=True)
        except Exception:
            pass
        added = 0
        for account in core.parse_accounts():
            if self.add_account(account.user_id, account.user_pw, silent=True):
                added += 1
        if added:
            LOG.log(f".env에서 계정 {added}개를 불러왔습니다.")
            self.save_profile_accounts()
        else:
            LOG.log(".env에서 새로 불러올 계정이 없습니다.")
        self._changed()
        return added

    def add_account(self, user_id, user_pw, silent=False):
        user_id = (user_id or "").strip()
        user_pw = (user_pw or "").strip()
        if not user_id:
            return False
        if any(a.user_id == user_id for a in self.accounts):
            if not silent:
                LOG.log(f"[!] 이미 등록된 계정입니다: {user_id}")
            return False
        account = core.Account(user_id, user_pw)
        account.gui_state = STATE_IDLE
        account.gui_mode = ""
        account.gui_selected = True
        self.accounts.append(account)
        if not silent:
            LOG.log(f"계정 추가: {user_id}")
            self.save_profile_accounts()
            self._changed()
        return True

    def remove_accounts(self, targets):
        for account in list(targets):
            self.close_browser(account)
            if account in self.accounts:
                self.accounts.remove(account)
                LOG.log(f"계정 삭제: {account.user_id}")
        self.save_profile_accounts()
        self._changed()

    def save_env(self):
        """계정 목록을 .env에 저장한다."""
        ids = ",".join(a.user_id for a in self.accounts)
        pws = ",".join(a.user_pw or "" for a in self.accounts)
        try:
            lines = []
            if os.path.exists(ENV_PATH):
                with open(ENV_PATH, "r", encoding="utf-8") as f:
                    lines = [ln.rstrip("\n") for ln in f
                             if not ln.strip().startswith(("CLASSCARD_ID=", "CLASSCARD_PW="))]
            lines = [ln for ln in lines if ln.strip()]
            lines.append(f"CLASSCARD_ID={ids}")
            lines.append(f"CLASSCARD_PW={pws}")
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            LOG.log(f"계정 {len(self.accounts)}개를 .env에 저장했습니다.")
            return True
        except Exception as e:
            LOG.log(f"[!] .env 저장 실패: {e}")
            return False

    def selected(self):
        chosen = [a for a in self.accounts if getattr(a, "gui_selected", True)]
        return chosen or list(self.accounts)

    # -- 설정 반영 ----------------------------------------------------------
    def apply_settings(self):
        s = self.settings
        core.AUTO_LOGIN = s.auto_login
        core.ANTI_BLUR = s.anti_blur
        core.CASCADE_WINDOWS = s.cascade
        core.WIN_W = max(1024, int(s.window_w))
        core.WIN_H = max(700, int(s.window_h))
        core.CHROME_BINARY = s.chrome_binary.strip()
        core.EXTRA_CHROME_ARGS = [a.strip() for a in s.extra_args.split() if a.strip()]
        s.save()

    # -- 브라우저 -----------------------------------------------------------
    def open_browsers(self, targets=None):
        targets = list(targets if targets is not None else self.selected())
        if not targets:
            LOG.log("[!] 브라우저를 열 계정이 없습니다.")
            return
        self.apply_settings()

        def worker():
            for i, account in enumerate(targets):
                if account.driver is not None:
                    LOG.log(f"{account.tag} 브라우저가 이미 열려 있습니다.")
                    continue
                index = self.accounts.index(account) if account in self.accounts else i
                try:
                    core.initialize_browser(account, index)
                except Exception as e:
                    LOG.log(f"{account.tag} [!] 브라우저 실행 실패: {e}")
                    account.gui_state = STATE_ERROR
                self._changed()
            self._changed()

        threading.Thread(target=worker, daemon=True).start()

    def close_browser(self, account):
        if account.driver is None:
            return
        try:
            if account.stop_event:
                account.stop_event.set()
            account.driver.quit()
            LOG.log(f"{account.tag} 브라우저를 닫았습니다.")
        except Exception as e:
            LOG.log(f"{account.tag} 브라우저 종료 중 오류(무시): {e}")
        finally:
            account.driver = None
            account.answer_dict = None
            account.gui_state = STATE_IDLE
            self._changed()

    def close_browsers(self, targets=None):
        for account in list(targets if targets is not None else self.accounts):
            self.close_browser(account)

    # -- 자동화 -------------------------------------------------------------
    def start_mode(self, mode_key, targets=None, delay=None, gap=None):
        mode = MODE_BY_KEY.get(mode_key)
        if mode is None:
            LOG.log(f"[!] 알 수 없는 모드: {mode_key}")
            return
        targets = [a for a in (targets if targets is not None else self.selected())
                   if a.driver is not None]
        if not targets:
            LOG.log("[!] 실행할 브라우저가 없습니다. 먼저 '브라우저 열기'를 눌러주세요.")
            return

        delay = self.settings.start_delay if delay is None else delay
        gap = self.settings.account_gap if gap is None else gap
        func = mode.callable()

        def worker():
            if delay > 0:
                LOG.log(f"{delay}초 후 '{mode.label}'을(를) 시작합니다...")
                for _ in range(int(delay * 10)):
                    time.sleep(0.1)
            for i, account in enumerate(targets):
                if i and gap > 0:
                    time.sleep(gap)
                account.gui_mode = mode.label
                LOG.log(f"{account.tag} ▶ {mode.label} 시작")
                try:
                    core.start_one(account, func, mode.needs_dict)
                except Exception as e:
                    LOG.log(f"{account.tag} [!] 시작 실패: {e}")
                    account.gui_state = STATE_ERROR
                self._changed()

        threading.Thread(target=worker, daemon=True).start()

    def stop(self, targets=None):
        targets = list(targets if targets is not None else self.accounts)
        stopped = 0
        for account in targets:
            with account.lock:
                if account.thread and account.thread.is_alive():
                    stopped += 1
                    if account.stop_event:
                        account.stop_event.set()
                    account.thread = None
            account.gui_state = STATE_READY if account.driver else STATE_IDLE
        LOG.log(f"자동화 중지 요청 ({stopped}개 계정)" if stopped
                else "실행 중인 자동화가 없습니다.")
        self._changed()

    def fetch_wordbook(self, targets=None):
        targets = [a for a in (targets if targets is not None else self.selected())
                   if a.driver is not None]
        if not targets:
            LOG.log("[!] 브라우저가 열린 계정이 없습니다.")
            return

        def worker():
            for account in targets:
                try:
                    data = core.HtmlParser.get_data(account.driver, output_path=None)
                    new_dict = core.Spell.dict_from_cards(data)
                    if new_dict:
                        account.answer_dict = new_dict
                        LOG.log(f"{account.tag} 단어장 갱신 완료 ({len(new_dict)}개)")
                    else:
                        LOG.log(f"{account.tag} 단어장 추출 실패 (학습 페이지인지 확인하세요)")
                except Exception as e:
                    LOG.log(f"{account.tag} 단어장 추출 오류: {e}")
            self._changed()

        threading.Thread(target=worker, daemon=True).start()

    def export_wordbook(self, account, path):
        try:
            data = core.HtmlParser.get_data(account.driver, output_path=path)
            return bool(data)
        except Exception as e:
            LOG.log(f"{account.tag} 단어장 저장 실패: {e}")
            return False

    def running_accounts(self):
        return [a for a in self.accounts if a.thread and a.thread.is_alive()]

    def is_running(self):
        return bool(self.running_accounts())

    # -- 전역 단축키 (CLI와 동일한 조합) ------------------------------------
    def start_hotkeys(self):
        if self._hotkey_listener is not None:
            return True
        if not core.HOTKEYS_AVAILABLE:
            LOG.log(f"[!] 전역 단축키를 사용할 수 없습니다: {core.HOTKEY_IMPORT_ERROR}")
            return False
        try:
            bindings = {combo: (lambda k=key: self.start_mode(k))
                        for combo, key in HOTKEY_MAP.items()}
            bindings['<ctrl>+e'] = lambda: self.stop()
            bindings['<ctrl>+m'] = lambda: self.fetch_wordbook()
            listener = core.GlobalHotKeys(bindings)
            listener.start()
            self._hotkey_listener = listener
            LOG.log("전역 단축키가 활성화되었습니다. (Ctrl+A, Ctrl+I, Ctrl+E ...)")
            return True
        except Exception as e:
            LOG.log(f"[!] 전역 단축키 등록 실패: {e}")
            return False

    def stop_hotkeys(self):
        if self._hotkey_listener is None:
            return
        try:
            self._hotkey_listener.stop()
        except Exception:
            pass
        self._hotkey_listener = None
        LOG.log("전역 단축키를 껐습니다.")

    # -- 상태 감시 ----------------------------------------------------------
    def start_monitor(self):
        if self._monitor:
            return

        def loop():
            while not self._monitor_stop.wait(0.6):
                dirty = False
                finished = []
                for account in list(self.accounts):
                    prev = getattr(account, "gui_state", STATE_IDLE)
                    running = bool(account.thread and account.thread.is_alive())
                    if running:
                        state = STATE_RUNNING
                    elif account.driver is None:
                        state = STATE_IDLE
                    elif prev == STATE_RUNNING:
                        state = STATE_DONE
                        finished.append(account)
                    elif prev in (STATE_DONE, STATE_ERROR):
                        state = prev
                    else:
                        state = STATE_READY
                    if prev != state:
                        if state == STATE_DONE:
                            LOG.log(f"{account.tag} ■ {account.gui_mode or '자동화'} 종료")
                        account.gui_state = state
                        dirty = True
                if finished and not self.settings.keep_browser:
                    for account in finished:
                        LOG.log(f"{account.tag} 자동화 종료 → 브라우저를 닫습니다. "
                                f"('자동화 후 브라우저 유지'가 꺼져 있음)")
                        self.close_browser(account)
                if dirty:
                    self._changed()

        self._monitor = threading.Thread(target=loop, daemon=True)
        self._monitor.start()

    def shutdown(self):
        self._monitor_stop.set()
        self.stop_hotkeys()
        for account in list(self.accounts):
            try:
                if account.stop_event:
                    account.stop_event.set()
            except Exception:
                pass
        # 프로그램을 끄면 남아있는 크롬 창도 함께 정리한다.
        self.close_browsers()
        self.settings.save()

    # -- 내부 ---------------------------------------------------------------
    def _changed(self):
        try:
            self._on_change()
        except Exception:
            pass
