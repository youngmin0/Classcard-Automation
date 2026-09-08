"""로그인 / 회원가입 창.

프로그램을 켜면 이 창이 먼저 뜨고, 로그인에 성공해야 메인 화면이 열린다.
계정 정보는 로컬 `users.db`에만 저장되며 비밀번호는 해시로만 보관한다. (auth.py)
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QFrame, QStackedWidget, QWidget, QMessageBox)

import auth
from gui_theme import PALETTE, APP_NAME, APP_VERSION
from gui_widgets import TabStrip, CheckBox, apply_shadow, hline


class LoginWindow(QDialog):
    """로그인/회원가입 창. 성공하면 `self.user`에 로그인한 사용자가 담긴다."""

    def __init__(self, store=None, parent=None):
        super().__init__(parent)
        self.store = store or auth.UserStore()
        self.user = None

        self.setWindowTitle(f"{APP_NAME} 로그인")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(420, 560)

        self._build_ui()
        first_run = self.store.count() == 0
        self.tabs.set_index(1 if first_run else 0)
        if first_run:
            self.hint.setText("처음 실행입니다. 사용할 계정을 먼저 만들어 주세요.")
            self.signup_id.setFocus()
        else:
            self.login_id.setFocus()

    # ── UI ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        shell = QVBoxLayout(self)
        shell.setContentsMargins(10, 10, 10, 10)

        self.root = QFrame()
        self.root.setObjectName("root")
        apply_shadow(self.root, blur=32, y=8, alpha=45)
        shell.addWidget(self.root)

        lay = QVBoxLayout(self.root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 상단(닫기 버튼 + 로고)
        top = QHBoxLayout()
        top.setContentsMargins(10, 8, 8, 0)
        top.addStretch(1)
        close = QPushButton("✕")
        close.setObjectName("winBtn")
        close.setProperty("danger", "true")
        close.setFixedSize(28, 26)
        close.clicked.connect(self.reject)
        top.addWidget(close)
        lay.addLayout(top)

        head = QVBoxLayout()
        head.setContentsMargins(28, 4, 28, 12)
        head.setSpacing(4)
        logo = QLabel("CC")
        logo.setFixedSize(46, 46)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"background:{PALETTE['primary']}; color:white; border-radius:14px;"
                           f"font-weight:800; font-size:17px;")
        logo_row = QHBoxLayout()
        logo_row.addStretch(1)
        logo_row.addWidget(logo)
        logo_row.addStretch(1)
        head.addLayout(logo_row)

        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:17px; font-weight:800;")
        ver = QLabel(APP_VERSION)
        ver.setObjectName("hintLabel")
        ver.setAlignment(Qt.AlignCenter)
        head.addWidget(title)
        head.addWidget(ver)
        lay.addLayout(head)

        self.tabs = TabStrip(["로그인", "회원가입"])
        self.tabs.settings_btn.hide()
        lay.addWidget(self.tabs)
        lay.addWidget(hline())

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_login_page())
        self.stack.addWidget(self._build_signup_page())
        lay.addWidget(self.stack, 1)
        self.tabs.changed.connect(self._switch_tab)

        self.hint = QLabel("계정 정보는 이 컴퓨터에만 저장됩니다.")
        self.hint.setObjectName("hintLabel")
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.setWordWrap(True)
        foot = QVBoxLayout()
        foot.setContentsMargins(24, 0, 24, 16)
        foot.addWidget(self.hint)
        lay.addLayout(foot)

    def _field(self, layout, label_text, placeholder, password=False):
        lb = QLabel(label_text)
        lb.setObjectName("sectionLabel")
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(34)
        if password:
            edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(lb)
        layout.addWidget(edit)
        return edit

    def _build_login_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 18, 28, 8)
        lay.setSpacing(6)

        self.login_id = self._field(lay, "아이디", "아이디를 입력하세요")
        lay.addSpacing(4)
        self.login_pw = self._field(lay, "비밀번호", "비밀번호를 입력하세요", password=True)

        row = QHBoxLayout()
        self.remember = CheckBox(checked=True)
        row.addWidget(self.remember)
        remember_label = QLabel("자동 로그인")
        remember_label.setObjectName("sectionLabel")
        remember_label.setCursor(Qt.PointingHandCursor)
        remember_label.mousePressEvent = lambda _e: self.remember.setChecked(
            not self.remember.isChecked())
        row.addWidget(remember_label)
        row.addStretch(1)
        lay.addSpacing(6)
        lay.addLayout(row)

        self.login_error = QLabel("")
        self.login_error.setWordWrap(True)
        self.login_error.setStyleSheet(f"color:{PALETTE['danger']}; font-size:11.5px;")
        lay.addWidget(self.login_error)

        self.login_btn = QPushButton("로그인")
        self.login_btn.setProperty("variant", "primary")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self._do_login)
        lay.addStretch(1)
        lay.addWidget(self.login_btn)

        switch = QPushButton("계정이 없으신가요?  회원가입")
        switch.setStyleSheet("border:none; background:transparent;")
        switch.setCursor(Qt.PointingHandCursor)
        switch.clicked.connect(lambda: self.tabs.set_index(1))
        lay.addWidget(switch)

        self.login_id.returnPressed.connect(self.login_pw.setFocus)
        self.login_pw.returnPressed.connect(self._do_login)
        return page

    def _build_signup_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 14, 28, 8)
        lay.setSpacing(6)

        self.signup_id = self._field(lay, "아이디", "영문·숫자·밑줄 4~20자")
        self.signup_pw = self._field(lay, "비밀번호", f"{auth.MIN_PASSWORD_LEN}자 이상",
                                     password=True)
        self.signup_pw2 = self._field(lay, "비밀번호 확인", "한 번 더 입력하세요", password=True)

        self.signup_error = QLabel("")
        self.signup_error.setWordWrap(True)
        self.signup_error.setStyleSheet(f"color:{PALETTE['danger']}; font-size:11.5px;")
        lay.addWidget(self.signup_error)

        self.signup_btn = QPushButton("회원가입하고 시작하기")
        self.signup_btn.setProperty("variant", "primary")
        self.signup_btn.setMinimumHeight(40)
        self.signup_btn.setCursor(Qt.PointingHandCursor)
        self.signup_btn.clicked.connect(self._do_signup)
        lay.addStretch(1)
        lay.addWidget(self.signup_btn)

        switch = QPushButton("이미 계정이 있으신가요?  로그인")
        switch.setStyleSheet("border:none; background:transparent;")
        switch.setCursor(Qt.PointingHandCursor)
        switch.clicked.connect(lambda: self.tabs.set_index(0))
        lay.addWidget(switch)

        self.signup_id.returnPressed.connect(self.signup_pw.setFocus)
        self.signup_pw.returnPressed.connect(self.signup_pw2.setFocus)
        self.signup_pw2.returnPressed.connect(self._do_signup)
        return page

    # ── 동작 ──────────────────────────────────────────────────────────────
    def _switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        self.login_error.setText("")
        self.signup_error.setText("")
        (self.login_id if index == 0 else self.signup_id).setFocus()

    def _do_login(self):
        self.login_error.setText("")
        try:
            user = self.store.login(self.login_id.text(), self.login_pw.text(),
                                    remember=self.remember.isChecked())
        except auth.AuthError as e:
            self.login_error.setText(str(e))
            self.login_pw.selectAll()
            self.login_pw.setFocus()
            return
        except Exception as e:                       # DB 손상 등
            QMessageBox.critical(self, "로그인", f"로그인 중 오류가 발생했습니다: {e}")
            return
        self.user = user
        self.accept()

    def _do_signup(self):
        self.signup_error.setText("")
        try:
            user = self.store.register(self.signup_id.text(), self.signup_pw.text(),
                                       self.signup_pw2.text())
        except auth.AuthError as e:
            self.signup_error.setText(str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "회원가입", f"회원가입 중 오류가 발생했습니다: {e}")
            return
        self.user = user
        self.accept()

    # 프레임리스 창 드래그 이동
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self.windowHandle()
            if handle is not None:
                handle.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)


def prompt_login(store=None, allow_auto=True):
    """자동 로그인 → 실패하면 로그인 창. 로그인한 User 또는 None을 돌려준다."""
    store = store or auth.UserStore()
    if allow_auto:
        try:
            user = store.auto_login()
            if user is not None:
                return user, store
        except Exception:
            pass
    window = LoginWindow(store)
    if window.exec() == QDialog.Accepted and window.user is not None:
        return window.user, store
    return None, store
