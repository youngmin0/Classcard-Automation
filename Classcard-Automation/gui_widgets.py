"""GUI 공용 위젯 모음 (카드, 토글 스위치, 타이틀바, 계정 행 등)."""

from PySide6.QtCore import (Qt, QSize, QRectF, QPoint, Property, QPropertyAnimation,
                            QEasingCurve, Signal)
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QPushButton, QVBoxLayout,
                               QHBoxLayout, QAbstractButton, QSizePolicy,
                               QGraphicsDropShadowEffect, QButtonGroup)

from gui_theme import PALETTE, APP_NAME, APP_VERSION


# ────────────────────────────────────────────────────────────────────────────
# 토글 스위치
# ────────────────────────────────────────────────────────────────────────────
class ToggleSwitch(QAbstractButton):
    """예시 프로그램의 on/off 스위치와 같은 모양의 토글."""

    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(42, 22)
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def get_knob(self):
        return self._pos

    def set_knob(self, value):
        self._pos = float(value)
        self.update()

    knob = Property(float, get_knob, set_knob)

    def sizeHint(self):
        return QSize(42, 22)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())

        off = QColor("#d5dae4")
        on = QColor(PALETTE["primary"])
        track = QColor(
            int(off.red() + (on.red() - off.red()) * self._pos),
            int(off.green() + (on.green() - off.green()) * self._pos),
            int(off.blue() + (on.blue() - off.blue()) * self._pos),
        )
        if not self.isEnabled():
            track = QColor("#e6e9ef")

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(track))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)

        d = r.height() - 6
        x = 3 + self._pos * (r.width() - d - 6)
        p.setBrush(QBrush(QColor("white")))
        p.drawEllipse(QRectF(x, 3, d, d))


class CheckBox(QAbstractButton):
    """체크 표시를 직접 그리는 체크박스 (외부 이미지 리소스가 필요 없다)."""

    def __init__(self, checked=True, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(16, 16)

    def sizeHint(self):
        return QSize(16, 16)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        box = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if self.isChecked():
            p.setPen(QPen(QColor(PALETTE["primary"]), 1))
            p.setBrush(QBrush(QColor(PALETTE["primary"])))
        else:
            p.setPen(QPen(QColor("#c8cddb"), 1))
            p.setBrush(QBrush(QColor("white")))
        p.drawRoundedRect(box, 4, 4)
        if self.isChecked():
            pen = QPen(QColor("white"), 2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            w, h = self.width(), self.height()
            p.drawPolyline([QPoint(int(w * 0.26), int(h * 0.52)),
                            QPoint(int(w * 0.43), int(h * 0.70)),
                            QPoint(int(w * 0.75), int(h * 0.32))])


# ────────────────────────────────────────────────────────────────────────────
# 카드(패널)
# ────────────────────────────────────────────────────────────────────────────
class Card(QFrame):
    """제목 + 내용 영역을 가진 흰색 라운드 패널."""

    def __init__(self, title, icon="", badge="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(6)
        if icon:
            ic = QLabel(icon)
            ic.setObjectName("cardTitle")
            head.addWidget(ic)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        head.addWidget(self.title_label)
        head.addStretch(1)
        self.badge_label = QLabel(badge)
        self.badge_label.setObjectName("cardBadge")
        head.addWidget(self.badge_label)
        outer.addLayout(head)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        outer.addLayout(self.body, 1)

    def set_badge(self, text):
        self.badge_label.setText(text)

    def add(self, widget, stretch=0):
        self.body.addWidget(widget, stretch)
        return widget

    def add_layout(self, layout, stretch=0):
        self.body.addLayout(layout, stretch)
        return layout


# ────────────────────────────────────────────────────────────────────────────
# 상태 점 (● 시스템 정상)
# ────────────────────────────────────────────────────────────────────────────
class StatusDot(QWidget):
    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self._color = QColor(color or PALETTE["ok"])
        self.setFixedSize(8, 8)

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._color))
        p.drawEllipse(0, 0, self.width(), self.height())


class Pill(QLabel):
    """작은 상태 뱃지 (대기 / 실행 중 / 완료 …)."""

    def __init__(self, text="대기", color=None, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(19)
        self.set_state(text, color or PALETTE["text_muted"])

    def set_state(self, text, color):
        self.setText(text)
        c = QColor(color)
        bg = QColor(c)
        bg.setAlpha(28)
        self.setStyleSheet(
            f"color:{c.name()}; background: rgba({bg.red()},{bg.green()},{bg.blue()},0.13);"
            f"border-radius:9px; padding:1px 8px; font-size:10.5px; font-weight:700;"
        )


# ────────────────────────────────────────────────────────────────────────────
# 타이틀바 (프레임리스 창 드래그 / 최소화 / 최대화 / 닫기)
# ────────────────────────────────────────────────────────────────────────────
class TitleBar(QWidget):
    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()
    logout_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(46)
        self._drag_pos = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 6, 8, 6)
        lay.setSpacing(8)

        logo = QLabel("CC")
        logo.setFixedSize(26, 26)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            f"background:{PALETTE['primary']}; color:white; border-radius:8px;"
            f"font-weight:800; font-size:11px;"
        )
        lay.addWidget(logo)

        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        lay.addWidget(title)

        ver = QLabel(APP_VERSION)
        ver.setObjectName("appVersion")
        lay.addWidget(ver)
        lay.addStretch(1)

        self.clock = QLabel("")
        self.clock.setObjectName("clockLabel")
        lay.addWidget(self.clock)

        # 로그인한 사용자 표시 + 로그아웃
        lay.addSpacing(10)
        self.user_chip = QLabel("")
        self.user_chip.setObjectName("userChip")
        self.user_chip.hide()
        lay.addWidget(self.user_chip)

        self.logout_btn = QPushButton("로그아웃")
        self.logout_btn.setObjectName("logoutBtn")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.setFixedHeight(24)
        self.logout_btn.hide()
        self.logout_btn.clicked.connect(self.logout_requested.emit)
        lay.addWidget(self.logout_btn)

        self.dot = StatusDot()
        lay.addSpacing(8)
        lay.addWidget(self.dot)
        self.status = QLabel("시스템 정상")
        self.status.setObjectName("statusLabel")
        lay.addWidget(self.status)
        lay.addSpacing(6)

        self.btn_min = self._win_button("─")
        self.btn_max = self._win_button("□")
        self.btn_close = self._win_button("✕", danger=True)
        self.btn_min.clicked.connect(self.minimize_requested.emit)
        self.btn_max.clicked.connect(self.maximize_requested.emit)
        self.btn_close.clicked.connect(self.close_requested.emit)
        for b in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(b)

    def _win_button(self, text, danger=False):
        b = QPushButton(text)
        b.setObjectName("winBtn")
        b.setFixedSize(30, 26)
        b.setCursor(Qt.ArrowCursor)
        if danger:
            b.setProperty("danger", "true")
        return b

    def set_status(self, text, color):
        self.status.setText(text)
        self.dot.set_color(color)

    def set_user(self, name):
        """로그인한 사용자 이름을 타이틀바에 표시한다. (None이면 숨김)"""
        if name:
            self.user_chip.setText(f"👤 {name}")
            self.user_chip.show()
            self.logout_btn.show()
        else:
            self.user_chip.hide()
            self.logout_btn.hide()

    # 창 드래그 이동
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            window = self.window()
            handle = window.windowHandle()
            if handle is not None:
                handle.startSystemMove()
                event.accept()
                return
            self._drag_pos = event.globalPosition().toPoint() - window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, _event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self.maximize_requested.emit()
        event.accept()


# ────────────────────────────────────────────────────────────────────────────
# 탭 (메인 / LOG)
# ────────────────────────────────────────────────────────────────────────────
class TabStrip(QWidget):
    changed = Signal(int)

    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.setObjectName("tabStrip")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 10, 0)
        lay.setSpacing(18)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for i, text in enumerate(labels):
            b = QPushButton(text)
            b.setObjectName("tabBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(i == 0)
            self.group.addButton(b, i)
            lay.addWidget(b)
        lay.addStretch(1)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("winBtn")
        self.settings_btn.setFixedSize(28, 26)
        self.settings_btn.setToolTip("환경설정")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        lay.addWidget(self.settings_btn)

        self.group.idClicked.connect(self.changed.emit)

    def set_index(self, index):
        btn = self.group.button(index)
        if btn:
            btn.setChecked(True)
            self.changed.emit(index)


# ────────────────────────────────────────────────────────────────────────────
# 학습 모드 버튼
# ────────────────────────────────────────────────────────────────────────────
class ModeButton(QPushButton):
    def __init__(self, mode, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.setObjectName("modeBtn")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setText(f"{mode.icon}  {mode.label}")
        self.setToolTip(f"{mode.desc}\n단축키: {mode.hotkey}")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


# ────────────────────────────────────────────────────────────────────────────
# 계정 리스트 한 줄
# ────────────────────────────────────────────────────────────────────────────
class AccountRow(QWidget):
    toggled = Signal()

    def __init__(self, account, parent=None):
        super().__init__(parent)
        self.account = account
        self.setFixedHeight(40)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 8, 2)
        lay.setSpacing(8)

        self.check = CheckBox(checked=True)
        self.check.toggled.connect(lambda _v: self.toggled.emit())
        lay.addWidget(self.check)

        name_box = QVBoxLayout()
        name_box.setSpacing(0)
        self.name = QLabel(account.user_id)
        self.name.setStyleSheet("font-size:12px; font-weight:700;")
        self.sub = QLabel("브라우저 꺼짐")
        self.sub.setObjectName("hintLabel")
        name_box.addWidget(self.name)
        name_box.addWidget(self.sub)
        lay.addLayout(name_box, 1)

        self.pill = Pill("대기", PALETTE["text_muted"])
        lay.addWidget(self.pill)

        self.setStyleSheet(
            "AccountRow { border-radius:9px; }"
            "AccountRow:hover { background: %s; }" % PALETTE["hover"]
        )

    @property
    def checked(self):
        return self.check.isChecked()

    def set_checked(self, value):
        self.check.setChecked(bool(value))

    def refresh(self, browser_text, state_text, color):
        self.sub.setText(browser_text)
        self.pill.set_state(state_text, color)


def apply_shadow(widget, blur=28, y=6, alpha=38):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(20, 26, 45, alpha))
    widget.setGraphicsEffect(effect)
    return effect


def hline(parent=None):
    line = QFrame(parent)
    line.setFrameShape(QFrame.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background:{PALETTE['line']}; border:none;")
    return line


def label(text, object_name=None, bold=False):
    lb = QLabel(text)
    if object_name:
        lb.setObjectName(object_name)
    if bold:
        f = lb.font()
        f.setWeight(QFont.DemiBold)
        lb.setFont(f)
    return lb
