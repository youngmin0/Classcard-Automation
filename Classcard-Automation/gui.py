"""클래스카드 자동화 GUI (PySide6).

실행:
    python gui.py
    python main.py --gui

CLI(단축키) 버전은 그대로 `python main.py` 로 쓸 수 있고,
GUI는 같은 자동화 엔진을 화면에서 조작할 수 있게 감싼 것이다.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal, QDate, QTime, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QTextCursor
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QGridLayout, QLabel, QPushButton, QLineEdit,
                               QListWidget, QListWidgetItem, QPlainTextEdit,
                               QStackedWidget, QScrollArea, QFrame, QSpinBox,
                               QTimeEdit, QDateEdit, QMessageBox, QFileDialog,
                               QButtonGroup, QDialog, QInputDialog, QProgressBar)

import gui_engine as engine_mod
from gui_engine import (Engine, LOG, MODES, MODE_BY_KEY, STATE_RUNNING,
                        STATE_READY, STATE_DONE, STATE_ERROR, STATE_IDLE, LOG_DIR)
from gui_theme import PALETTE, APP_NAME, APP_VERSION, stylesheet
from gui_widgets import (Card, TitleBar, TabStrip, ToggleSwitch, ModeButton,
                         AccountRow, apply_shadow, hline)

STATE_COLORS = {
    STATE_IDLE: PALETTE["text_muted"],
    STATE_READY: PALETTE["primary"],
    STATE_RUNNING: PALETTE["ok"],
    STATE_DONE: PALETTE["warn"],
    STATE_ERROR: PALETTE["danger"],
}


def app_icon() -> QIcon:
    """외부 이미지 파일 없이 코드로 그리는 앱 아이콘."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(PALETTE["primary"]))
    p.drawRoundedRect(2, 2, 60, 60, 16, 16)
    p.setPen(QColor("white"))
    f = QFont()
    f.setPointSize(22)
    f.setBold(True)
    p.setFont(f)
    p.drawText(pix.rect(), Qt.AlignCenter, "CC")
    p.end()
    return QIcon(pix)


class StatTile(QFrame):
    """숫자 + 설명이 들어가는 작은 상태 타일."""

    def __init__(self, caption, value="0", color=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background:{PALETTE['page']}; border:1px solid {PALETTE['card_border']};"
            f" border-radius:10px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(1)
        self.value = QLabel(value)
        self.value.setStyleSheet(
            f"font-size:17px; font-weight:800; color:{color or PALETTE['text']}; border:none;")
        cap = QLabel(caption)
        cap.setStyleSheet(f"font-size:10.5px; color:{PALETTE['text_muted']}; border:none;")
        lay.addWidget(self.value)
        lay.addWidget(cap)

    def set_value(self, value):
        self.value.setText(str(value))


class SettingsDialog(QDialog):
    """톱니바퀴(환경설정) 창 — 크롬 실행 옵션과 로그 폴더."""

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle("환경설정")
        self.setMinimumWidth(420)
        self.setStyleSheet(stylesheet())

        s = engine.settings
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        title = QLabel("환경설정")
        title.setObjectName("cardTitle")
        root.addWidget(title)
        root.addWidget(hline())

        root.addWidget(QLabel("크롬 실행 파일 경로 (비우면 자동 탐색)"))
        path_row = QHBoxLayout()
        self.chrome_edit = QLineEdit(s.chrome_binary)
        self.chrome_edit.setPlaceholderText(r"예: C:\Program Files\Google\Chrome\Application\chrome.exe")
        browse = QPushButton("찾아보기")
        browse.clicked.connect(self._browse)
        path_row.addWidget(self.chrome_edit, 1)
        path_row.addWidget(browse)
        root.addLayout(path_row)

        root.addWidget(QLabel("추가 크롬 실행 인자 (공백으로 구분)"))
        self.args_edit = QLineEdit(s.extra_args)
        self.args_edit.setPlaceholderText("예: --lang=ko-KR --mute-audio")
        root.addWidget(self.args_edit)

        root.addWidget(hline())
        info = QLabel(f"계정 파일: {engine_mod.ENV_PATH}\n로그 폴더: {LOG_DIR}")
        info.setObjectName("hintLabel")
        info.setWordWrap(True)
        root.addWidget(info)

        btn_row = QHBoxLayout()
        open_logs = QPushButton("로그 폴더 열기")
        open_logs.clicked.connect(self._open_logs)
        btn_row.addWidget(open_logs)
        btn_row.addStretch(1)
        cancel = QPushButton("취소")
        cancel.clicked.connect(self.reject)
        save = QPushButton("저장")
        save.setProperty("variant", "primary")
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        root.addLayout(btn_row)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "크롬 실행 파일 선택", "", "실행 파일 (*.exe);;모든 파일 (*)")
        if path:
            self.chrome_edit.setText(path)

    def _open_logs(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(LOG_DIR)  # noqa: S606
            elif sys.platform == "darwin":
                os.system(f'open "{LOG_DIR}"')
            else:
                os.system(f'xdg-open "{LOG_DIR}"')
        except Exception as e:
            QMessageBox.warning(self, "로그 폴더", f"폴더를 열지 못했습니다: {e}")

    def _save(self):
        self.engine.settings.chrome_binary = self.chrome_edit.text().strip()
        self.engine.settings.extra_args = self.args_edit.text().strip()
        self.engine.apply_settings()
        LOG.log("환경설정을 저장했습니다.")
        self.accept()


class MainWindow(QWidget):
    log_line = Signal(str)
    state_changed = Signal()

    RESIZE_MARGIN = 6

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(1000, 660)
        self.resize(1080, 720)
        self.setMouseTracking(True)

        self.engine = Engine(on_change=self.state_changed.emit)
        self.rows = {}                 # account -> AccountRow
        self._pending_mode = None      # 브라우저가 열리면 자동으로 시작할 모드
        self._schedule_fired_at = None

        self._build_ui()
        self._connect()
        self._restore_settings()

        LOG.install()
        LOG.subscribe(lambda line: self.log_line.emit(line))
        self.engine.start_monitor()
        self.engine.apply_settings()
        self.engine.load_env_accounts()
        if self.engine.settings.hotkeys:
            if not self.engine.start_hotkeys():
                self.sw_hotkeys.setChecked(False)
        LOG.log(f"{APP_NAME} {APP_VERSION} 준비 완료.")

    # ── UI 구성 ────────────────────────────────────────────────────────────
    def _build_ui(self):
        shell = QVBoxLayout(self)
        shell.setContentsMargins(10, 10, 10, 10)   # 그림자 여백

        self.root = QFrame()
        self.root.setObjectName("root")
        apply_shadow(self.root, blur=32, y=8, alpha=45)
        shell.addWidget(self.root)

        root_lay = QVBoxLayout(self.root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        self.title_bar = TitleBar()
        root_lay.addWidget(self.title_bar)

        self.tabs = TabStrip(["메인", "LOG"])
        root_lay.addWidget(self.tabs)
        root_lay.addWidget(hline())

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_main_page())
        self.stack.addWidget(self._build_log_page())
        root_lay.addWidget(self.stack, 1)

    # -- 메인 탭 -------------------------------------------------------------
    def _build_main_page(self):
        page = QWidget()
        lay = QHBoxLayout(page)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.setSpacing(12)

        lay.addWidget(self._build_account_card(), 0)

        middle = QVBoxLayout()
        middle.setSpacing(12)
        middle.addWidget(self._build_mode_card(), 0)
        middle.addWidget(self._build_options_card(), 1)
        lay.addLayout(middle, 1)

        lay.addWidget(self._build_run_card(), 0)
        return page

    def _build_account_card(self):
        card = Card("계정 리스트", icon="👥")
        card.setFixedWidth(300)

        add_row = QHBoxLayout()
        add_row.setSpacing(6)
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("아이디")
        self.pw_edit = QLineEdit()
        self.pw_edit.setPlaceholderText("비밀번호")
        self.pw_edit.setEchoMode(QLineEdit.Password)
        self.add_btn = QPushButton("＋")
        self.add_btn.setFixedWidth(34)
        self.add_btn.setToolTip("계정 추가")
        add_row.addWidget(self.id_edit, 3)
        add_row.addWidget(self.pw_edit, 3)
        add_row.addWidget(self.add_btn, 0)
        card.add_layout(add_row)

        grid = QGridLayout()
        grid.setSpacing(6)
        self.btn_load_env = QPushButton("⭳  .env 불러오기")
        self.btn_save_env = QPushButton("⭱  계정 저장")
        self.btn_open = QPushButton("🌐  브라우저 열기")
        self.btn_close = QPushButton("⛌  브라우저 닫기")
        self.btn_select_all = QPushButton("☑  전체 선택")
        self.btn_delete = QPushButton("🗑  선택 삭제")
        self.btn_delete.setProperty("variant", "danger")
        for i, b in enumerate([self.btn_load_env, self.btn_save_env, self.btn_open,
                               self.btn_close, self.btn_select_all, self.btn_delete]):
            grid.addWidget(b, i // 2, i % 2)
        card.add_layout(grid)

        card.add(hline())

        head = QHBoxLayout()
        self.account_count = QLabel("계정 0 · 실행 0")
        self.account_count.setObjectName("sectionLabel")
        head.addWidget(self.account_count)
        head.addStretch(1)
        card.add_layout(head)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("검색…")
        self.search_edit.setClearButtonEnabled(True)
        card.add(self.search_edit)

        self.account_list = QListWidget()
        self.account_list.setSelectionMode(QListWidget.NoSelection)
        self.account_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.account_list.setSpacing(2)
        self.account_list.setToolTip("더블클릭하면 비밀번호를 바꿀 수 있습니다.")

        self.empty_label = QLabel("계정을 추가하세요\n(.env 불러오기도 가능합니다)")
        self.empty_label.setObjectName("emptyLabel")
        self.empty_label.setAlignment(Qt.AlignCenter)

        self.list_stack = QStackedWidget()
        self.list_stack.addWidget(self.account_list)
        self.list_stack.addWidget(self.empty_label)
        self.list_stack.setCurrentIndex(1)
        card.add(self.list_stack, 1)
        return card

    def _build_mode_card(self):
        card = Card("학습 모드", icon="🎯", badge="한 가지를 선택하세요")
        grid = QGridLayout()
        grid.setSpacing(6)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        for i, mode in enumerate(MODES):
            btn = ModeButton(mode)
            self.mode_group.addButton(btn, i)
            grid.addWidget(btn, i // 3, i % 3)
        card.add_layout(grid)

        self.mode_desc = QLabel("")
        self.mode_desc.setObjectName("hintLabel")
        self.mode_desc.setWordWrap(True)
        card.add(self.mode_desc)
        return card

    def _option_row(self, text, widget, hint=""):
        row = QHBoxLayout()
        row.setSpacing(8)
        box = QVBoxLayout()
        box.setSpacing(0)
        lb = QLabel(text)
        lb.setObjectName("sectionLabel")
        lb.setWordWrap(True)
        box.addWidget(lb)
        if hint:
            hb = QLabel(hint)
            hb.setObjectName("hintLabel")
            hb.setWordWrap(True)
            hb.setMinimumWidth(1)
            box.addWidget(hb)
        row.addLayout(box, 1)
        row.addWidget(widget, 0, Qt.AlignRight | Qt.AlignVCenter)
        return row

    def _build_options_card(self):
        card = Card("고급 설정", icon="⚙")

        inner = QWidget()
        form = QVBoxLayout(inner)
        form.setContentsMargins(0, 0, 6, 0)
        form.setSpacing(10)

        self.sw_auto_login = ToggleSwitch(checked=True)
        self.sw_anti_blur = ToggleSwitch(checked=True)
        self.sw_cascade = ToggleSwitch(checked=True)
        self.sw_keep_browser = ToggleSwitch(checked=True)
        self.sw_hotkeys = ToggleSwitch(checked=True)
        self.sw_schedule = ToggleSwitch(checked=False)

        form.addLayout(self._option_row("자동 로그인", self.sw_auto_login,
                                        ".env에 저장된 ID/PW로 바로 로그인"))
        form.addLayout(self._option_row("백그라운드 실행", self.sw_anti_blur,
                                        "창이 가려져도 '이탈'로 잡히지 않게 처리"))
        form.addLayout(self._option_row("창 계단식 배치", self.sw_cascade,
                                        "계정마다 크롬 창을 어긋나게 띄움"))
        form.addLayout(self._option_row("자동화 후 브라우저 유지", self.sw_keep_browser,
                                        "끄면 자동화가 끝날 때 크롬을 닫음"))
        form.addLayout(self._option_row("전역 단축키 사용", self.sw_hotkeys,
                                        "Ctrl+A / Ctrl+I / Ctrl+E … (CLI와 동일)"))
        form.addWidget(hline())

        self.spin_delay = QSpinBox()
        self.spin_delay.setRange(0, 3600)
        self.spin_delay.setFixedWidth(84)
        self.spin_gap = QSpinBox()
        self.spin_gap.setRange(0, 600)
        self.spin_gap.setFixedWidth(84)
        form.addLayout(self._option_row("시작 지연시간 (초)", self.spin_delay,
                                        "시작 버튼을 누른 뒤 대기할 시간"))
        form.addLayout(self._option_row("계정별 실행 간격 (초)", self.spin_gap,
                                        "다계정 병렬 실행 시 간격"))

        size_box = QWidget()
        size_lay = QHBoxLayout(size_box)
        size_lay.setContentsMargins(0, 0, 0, 0)
        size_lay.setSpacing(4)
        self.spin_w = QSpinBox()
        self.spin_w.setRange(1024, 3840)
        self.spin_w.setFixedWidth(74)
        self.spin_h = QSpinBox()
        self.spin_h.setRange(700, 2160)
        self.spin_h.setFixedWidth(74)
        size_lay.addWidget(self.spin_w)
        size_lay.addWidget(QLabel("×"))
        size_lay.addWidget(self.spin_h)
        form.addLayout(self._option_row("크롬 창 크기", size_box,
                                        "좁으면 모바일 레이아웃이 되어 자동화가 깨집니다"))

        form.addWidget(hline())
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setFixedWidth(96)
        form.addLayout(self._option_row("예약 실행", self.sw_schedule,
                                        "지정한 시각에 선택한 모드를 자동 시작"))
        form.addLayout(self._option_row("예약시간", self.time_edit))
        form.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        scroll.setFrameShape(QFrame.NoFrame)
        card.add(scroll, 1)
        return card

    def _build_run_card(self):
        card = Card("실행 상태", icon="▤")
        card.setFixedWidth(320)

        tiles = QHBoxLayout()
        tiles.setSpacing(6)
        self.tile_accounts = StatTile("등록 계정")
        self.tile_browsers = StatTile("브라우저", color=PALETTE["primary"])
        self.tile_running = StatTile("실행 중", color=PALETTE["ok"])
        for t in (self.tile_accounts, self.tile_browsers, self.tile_running):
            tiles.addWidget(t)
        card.add_layout(tiles)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        card.add(self.progress)

        self.mini_log = QPlainTextEdit()
        self.mini_log.setObjectName("miniLog")
        self.mini_log.setReadOnly(True)
        self.mini_log.setMaximumBlockCount(400)
        card.add(self.mini_log, 1)

        hint = QLabel("Ctrl + A 전체 · Ctrl + E 중지 · Ctrl + M 단어장")
        hint.setObjectName("hintLabel")
        hint.setAlignment(Qt.AlignCenter)
        card.add(hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_fetch = QPushButton("📥  단어장 가져오기")
        self.btn_export = QPushButton("💾  data.json 저장")
        btn_row.addWidget(self.btn_fetch)
        btn_row.addWidget(self.btn_export)
        card.add_layout(btn_row)

        self.cta = QPushButton("▶  자동화 시작")
        self.cta.setObjectName("ctaBtn")
        self.cta.setCursor(Qt.PointingHandCursor)
        self.cta.setMinimumHeight(44)
        card.add(self.cta)
        return card

    # -- LOG 탭 --------------------------------------------------------------
    def _build_log_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("▤  LOG")
        title.setObjectName("cardTitle")
        head.addWidget(title)
        self.log_date = QDateEdit(QDate.currentDate())
        self.log_date.setCalendarPopup(True)
        self.log_date.setDisplayFormat("yyyy-MM-dd")
        self.log_date.setFixedWidth(120)
        head.addWidget(self.log_date)
        head.addStretch(1)
        self.btn_log_save = QPushButton("💾  저장")
        self.btn_log_clear = QPushButton("🗑  지우기")
        self.btn_log_clear.setProperty("variant", "danger")
        head.addWidget(self.btn_log_save)
        head.addWidget(self.btn_log_clear)
        lay.addLayout(head)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(20000)
        lay.addWidget(self.log_view, 1)
        return page

    # ── 시그널 연결 ────────────────────────────────────────────────────────
    def _connect(self):
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_requested.connect(self._toggle_max)
        self.title_bar.close_requested.connect(self.close)
        self.tabs.changed.connect(self.stack.setCurrentIndex)
        self.tabs.settings_btn.clicked.connect(self._open_settings)

        self.log_line.connect(self._append_log)
        self.state_changed.connect(self._refresh)

        self.add_btn.clicked.connect(self._add_account)
        self.id_edit.returnPressed.connect(lambda: self.pw_edit.setFocus())
        self.pw_edit.returnPressed.connect(self._add_account)
        self.btn_load_env.clicked.connect(self.engine.load_env_accounts)
        self.btn_save_env.clicked.connect(self._save_env)
        self.btn_open.clicked.connect(lambda: self.engine.open_browsers())
        self.btn_close.clicked.connect(lambda: self.engine.close_browsers(self.engine.selected()))
        self.btn_select_all.clicked.connect(self._toggle_select_all)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.search_edit.textChanged.connect(self._apply_filter)
        self.account_list.itemDoubleClicked.connect(self._edit_password)

        self.mode_group.idToggled.connect(self._mode_changed)
        self.btn_fetch.clicked.connect(lambda: self.engine.fetch_wordbook())
        self.btn_export.clicked.connect(self._export_wordbook)
        self.cta.clicked.connect(self._toggle_run)

        self.sw_hotkeys.toggled.connect(self._hotkeys_toggled)
        for sw in (self.sw_auto_login, self.sw_anti_blur, self.sw_cascade,
                   self.sw_keep_browser, self.sw_schedule):
            sw.toggled.connect(self._save_settings)
        for sp in (self.spin_delay, self.spin_gap, self.spin_w, self.spin_h):
            sp.valueChanged.connect(self._save_settings)
        self.time_edit.timeChanged.connect(self._save_settings)

        self.log_date.dateChanged.connect(self._load_log_day)
        self.btn_log_save.clicked.connect(self._save_log)
        self.btn_log_clear.clicked.connect(self._clear_log)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _restore_settings(self):
        s = self.engine.settings
        self.sw_auto_login.setChecked(s.auto_login)
        self.sw_anti_blur.setChecked(s.anti_blur)
        self.sw_cascade.setChecked(s.cascade)
        self.sw_keep_browser.setChecked(s.keep_browser)
        self.sw_hotkeys.setChecked(s.hotkeys)
        self.sw_schedule.setChecked(s.schedule_enabled)
        self.spin_delay.setValue(s.start_delay)
        self.spin_gap.setValue(s.account_gap)
        self.spin_w.setValue(s.window_w)
        self.spin_h.setValue(s.window_h)
        self.time_edit.setTime(QTime.fromString(s.schedule_time, "HH:mm:ss"))

        index = next((i for i, m in enumerate(MODES) if m.key == s.selected_mode), 0)
        button = self.mode_group.button(index)
        if button:
            button.setChecked(True)
            self.mode_desc.setText(MODES[index].desc + f"  ({MODES[index].hotkey})")

        self.log_view.setPlainText(LOG.read_day(datetime.now().strftime("%Y-%m-%d")))

    # ── 동작 ───────────────────────────────────────────────────────────────
    def _current_mode(self):
        index = self.mode_group.checkedId()
        return MODES[index] if 0 <= index < len(MODES) else MODES[0]

    def _mode_changed(self, index, checked):
        if not checked:
            return
        mode = MODES[index]
        self.mode_desc.setText(f"{mode.desc}  ({mode.hotkey})")
        self.engine.settings.selected_mode = mode.key
        self.engine.settings.save()

    def _save_settings(self, *_):
        s = self.engine.settings
        s.auto_login = self.sw_auto_login.isChecked()
        s.anti_blur = self.sw_anti_blur.isChecked()
        s.cascade = self.sw_cascade.isChecked()
        s.keep_browser = self.sw_keep_browser.isChecked()
        s.hotkeys = self.sw_hotkeys.isChecked()
        s.schedule_enabled = self.sw_schedule.isChecked()
        s.start_delay = self.spin_delay.value()
        s.account_gap = self.spin_gap.value()
        s.window_w = self.spin_w.value()
        s.window_h = self.spin_h.value()
        s.schedule_time = self.time_edit.time().toString("HH:mm:ss")
        self.engine.apply_settings()

    def _hotkeys_toggled(self, checked):
        if checked:
            if not self.engine.start_hotkeys():
                self.sw_hotkeys.blockSignals(True)
                self.sw_hotkeys.setChecked(False)
                self.sw_hotkeys.blockSignals(False)
        else:
            self.engine.stop_hotkeys()
        self._save_settings()

    def _add_account(self):
        user_id = self.id_edit.text().strip()
        user_pw = self.pw_edit.text()
        if not user_id:
            QMessageBox.information(self, "계정 추가", "아이디를 입력하세요.")
            return
        if self.engine.add_account(user_id, user_pw):
            self.id_edit.clear()
            self.pw_edit.clear()
            self.id_edit.setFocus()

    def _save_env(self):
        if not self.engine.accounts:
            QMessageBox.information(self, "계정 저장", "저장할 계정이 없습니다.")
            return
        if self.engine.save_env():
            QMessageBox.information(self, "계정 저장",
                                    f".env에 계정 {len(self.engine.accounts)}개를 저장했습니다.\n"
                                    f"{engine_mod.ENV_PATH}")

    def _toggle_select_all(self):
        target = not all(row.checked for row in self.rows.values()) if self.rows else True
        for row in self.rows.values():
            row.set_checked(target)

    def _delete_selected(self):
        targets = [a for a in self.engine.accounts if getattr(a, "gui_selected", True)]
        if not targets:
            return
        answer = QMessageBox.question(
            self, "계정 삭제",
            f"선택한 계정 {len(targets)}개를 목록에서 지울까요?\n(.env 파일은 '계정 저장'을 눌러야 반영됩니다)")
        if answer == QMessageBox.Yes:
            self.engine.remove_accounts(targets)

    def _edit_password(self, item):
        account = item.data(Qt.UserRole)
        if account is None:
            return
        text, ok = QInputDialog.getText(self, "비밀번호 변경",
                                        f"[{account.user_id}] 비밀번호",
                                        QLineEdit.Password, account.user_pw or "")
        if ok:
            account.user_pw = text
            LOG.log(f"{account.tag} 비밀번호를 변경했습니다. ('계정 저장'으로 .env에 반영)")

    def _export_wordbook(self):
        targets = [a for a in self.engine.selected() if a.driver is not None]
        if not targets:
            QMessageBox.information(self, "data.json 저장", "브라우저가 열린 계정이 없습니다.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "단어장 저장", os.path.join(engine_mod.BASE_DIR, "data.json"), "JSON (*.json)")
        if not path:
            return
        if self.engine.export_wordbook(targets[0], path):
            QMessageBox.information(self, "data.json 저장", f"저장했습니다.\n{path}")
        else:
            QMessageBox.warning(self, "data.json 저장", "단어장을 추출하지 못했습니다. 학습 페이지인지 확인하세요.")

    def _toggle_run(self):
        if self.engine.is_running():
            self.engine.stop()
            self._pending_mode = None
            return

        if not self.engine.accounts:
            QMessageBox.information(self, "자동화 시작", "먼저 계정을 추가하세요.")
            return

        mode = self._current_mode()
        targets = self.engine.selected()
        if not any(a.driver is not None for a in targets):
            answer = QMessageBox.question(
                self, "자동화 시작",
                "브라우저가 열려 있지 않습니다. 지금 열고 이어서 시작할까요?")
            if answer != QMessageBox.Yes:
                return
            self._pending_mode = mode.key
            self.engine.open_browsers(targets)
            LOG.log(f"브라우저가 준비되면 '{mode.label}'을(를) 자동으로 시작합니다.")
            return

        self.engine.start_mode(mode.key, targets)

    # ── 화면 갱신 ──────────────────────────────────────────────────────────
    def _refresh(self):
        accounts = list(self.engine.accounts)

        if list(self.rows.keys()) != accounts:
            self.account_list.clear()
            self.rows.clear()
            for account in accounts:
                row = AccountRow(account)
                row.set_checked(getattr(account, "gui_selected", True))
                row.toggled.connect(self._sync_selection)
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, 44))
                item.setData(Qt.UserRole, account)
                self.account_list.addItem(item)
                self.account_list.setItemWidget(item, row)
                self.rows[account] = row
            self._apply_filter(self.search_edit.text())

        running = 0
        opened = 0
        for account, row in self.rows.items():
            state = getattr(account, "gui_state", STATE_IDLE)
            if state == STATE_RUNNING:
                running += 1
            if account.driver is not None:
                opened += 1
            browser_text = "브라우저 열림" if account.driver is not None else "브라우저 꺼짐"
            if state == STATE_RUNNING and getattr(account, "gui_mode", ""):
                browser_text = f"{account.gui_mode} 진행 중"
            row.refresh(browser_text, state, STATE_COLORS.get(state, PALETTE["text_muted"]))

        self.list_stack.setCurrentIndex(0 if accounts else 1)
        self.account_count.setText(f"계정 {len(accounts)} · 실행 {running}")
        self.tile_accounts.set_value(len(accounts))
        self.tile_browsers.set_value(opened)
        self.tile_running.set_value(running)

        is_running = running > 0
        self.cta.setText("■  자동화 중지" if is_running else "▶  자동화 시작")
        self.cta.setProperty("running", "true" if is_running else "false")
        self.cta.style().unpolish(self.cta)
        self.cta.style().polish(self.cta)
        if is_running:
            self.progress.setRange(0, 0)          # 진행률을 알 수 없으므로 무한 표시
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
        self.title_bar.set_status(
            f"자동화 실행 중 ({running})" if is_running else "시스템 정상",
            PALETTE["ok"] if not is_running else PALETTE["primary"])

        # 브라우저 준비를 기다리던 예약 시작 처리
        if self._pending_mode and opened > 0 and not is_running:
            mode_key, self._pending_mode = self._pending_mode, None
            self.engine.start_mode(mode_key)

    def _sync_selection(self):
        for account, row in self.rows.items():
            account.gui_selected = row.checked

    def _apply_filter(self, text=""):
        needle = (text or "").strip().lower()
        for i in range(self.account_list.count()):
            item = self.account_list.item(i)
            account = item.data(Qt.UserRole)
            item.setHidden(bool(needle) and needle not in account.user_id.lower())

    LOG_COLORS = (
        (("[!]", "오류", "실패", "Error", "Traceback"), "#ff8787"),
        (("[O]", "완료", "성공", "▶"), "#8ce99a"),
        (("[예약]", "시작", "■"), "#74c0fc"),
    )

    def _log_color(self, line):
        for keywords, color in self.LOG_COLORS:
            if any(k in line for k in keywords):
                return color
        return None

    def _append_log(self, line):
        today = self.log_date.date() == QDate.currentDate()
        color = self._log_color(line)
        text = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if today:
            # 색을 명시하지 않으면 직전 줄의 색을 그대로 물려받으므로 항상 지정한다.
            self.log_view.appendHtml(
                f'<span style="color:{color or PALETTE["log_text"]}; white-space:pre-wrap;">'
                f'{text}</span>')
            self.log_view.moveCursor(QTextCursor.End)
        self.mini_log.appendPlainText(line)
        self.mini_log.moveCursor(QTextCursor.End)

    def _load_log_day(self, qdate):
        date_str = qdate.toString("yyyy-MM-dd")
        self.log_view.setPlainText(LOG.read_day(date_str) or "(해당 날짜의 로그가 없습니다)")
        self.log_view.moveCursor(QTextCursor.End)

    def _save_log(self):
        date_str = self.log_date.date().toString("yyyy-MM-dd")
        path, _ = QFileDialog.getSaveFileName(
            self, "로그 저장", os.path.join(os.path.expanduser("~"), f"classcard-{date_str}.log"),
            "로그 파일 (*.log);;텍스트 (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_view.toPlainText())
            QMessageBox.information(self, "로그 저장", f"저장했습니다.\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "로그 저장", f"저장하지 못했습니다: {e}")

    def _clear_log(self):
        date_str = self.log_date.date().toString("yyyy-MM-dd")
        if QMessageBox.question(self, "로그 지우기", f"{date_str} 로그를 지울까요?") != QMessageBox.Yes:
            return
        LOG.clear_day(date_str)
        self.log_view.clear()
        if date_str == datetime.now().strftime("%Y-%m-%d"):
            self.mini_log.clear()

    def _tick(self):
        now = datetime.now()
        self.title_bar.clock.setText(now.strftime("%Y년 %m월 %d일 %H시 %M분 %S초"))

        if not self.engine.settings.schedule_enabled:
            self._schedule_fired_at = None
            return
        target = self.engine.settings.schedule_time
        current = now.strftime("%H:%M:%S")
        today_key = now.strftime("%Y-%m-%d ") + target
        if current == target and self._schedule_fired_at != today_key:
            self._schedule_fired_at = today_key
            mode = self._current_mode()
            LOG.log(f"[예약] {target} — '{mode.label}'을(를) 시작합니다.")
            if not self.engine.is_running():
                self._toggle_run()

    def _open_settings(self):
        SettingsDialog(self.engine, self).exec()

    # ── 프레임리스 창(이동/크기 조절/닫기) ─────────────────────────────────
    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
            self.layout().setContentsMargins(10, 10, 10, 10)
            self.root.setProperty("maximized", "false")
        else:
            self.showMaximized()
            self.layout().setContentsMargins(0, 0, 0, 0)
            self.root.setProperty("maximized", "true")
        self.root.style().unpolish(self.root)
        self.root.style().polish(self.root)

    def _edges_at(self, pos):
        m = self.RESIZE_MARGIN
        edges = Qt.Edges()
        if pos.x() <= m + 8:
            edges |= Qt.LeftEdge
        if pos.x() >= self.width() - m - 8:
            edges |= Qt.RightEdge
        if pos.y() <= m + 8:
            edges |= Qt.TopEdge
        if pos.y() >= self.height() - m - 8:
            edges |= Qt.BottomEdge
        return edges

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.isMaximized():
            edges = self._edges_at(event.position().toPoint())
            if edges:
                handle = self.windowHandle()
                if handle is not None:
                    handle.startSystemResize(edges)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isMaximized():
            self.unsetCursor()
            return super().mouseMoveEvent(event)
        edges = self._edges_at(event.position().toPoint())
        if edges in (Qt.LeftEdge | Qt.TopEdge, Qt.RightEdge | Qt.BottomEdge):
            self.setCursor(Qt.SizeFDiagCursor)
        elif edges in (Qt.RightEdge | Qt.TopEdge, Qt.LeftEdge | Qt.BottomEdge):
            self.setCursor(Qt.SizeBDiagCursor)
        elif edges & (Qt.LeftEdge | Qt.RightEdge):
            self.setCursor(Qt.SizeHorCursor)
        elif edges & (Qt.TopEdge | Qt.BottomEdge):
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def closeEvent(self, event):
        if self.engine.is_running():
            answer = QMessageBox.question(
                self, "종료", "자동화가 실행 중입니다. 정말 종료할까요?\n(열려 있는 크롬 창도 함께 닫힙니다)")
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        self._save_settings()
        self.timer.stop()
        self.engine.shutdown()
        LOG.uninstall()
        event.accept()


def main():
    QApplication.setApplicationName(APP_NAME)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setWindowIcon(app_icon())
    app.setStyleSheet(stylesheet())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
