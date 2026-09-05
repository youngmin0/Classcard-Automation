"""GUI 색상 팔레트 / 폰트 / 스타일시트.

색을 바꾸고 싶으면 PALETTE 값만 수정하면 전체 UI에 반영된다.
"""

APP_NAME = "클래스카드 자동화"
APP_VERSION = "v2.0.0"

# 한글이 깨지지 않도록 OS별 기본 한글 폰트를 순서대로 지정한다.
FONT_STACK = ('"Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo", '
              '"Noto Sans KR", "NanumGothic", "Segoe UI", sans-serif')
MONO_STACK = ('"D2Coding", "Consolas", "D2Coding ligature", "Menlo", '
              '"DejaVu Sans Mono", monospace')

PALETTE = {
    "window":      "#e9ecf2",   # 창 바깥(그림자) 영역
    "page":        "#f6f7fa",   # 본문 배경
    "card":        "#ffffff",
    "card_border": "#e6e9ef",
    "text":        "#1b1f27",
    "text_sub":    "#5f6673",
    "text_muted":  "#9aa2b1",
    "primary":     "#4c6ef5",
    "primary_dk":  "#3b5bdb",
    "primary_lt":  "#eef1ff",
    "accent":      "#ffd43b",   # 시작 버튼(포인트 컬러)
    "accent_dk":   "#fcc419",
    "ok":          "#2fb344",
    "warn":        "#f59f00",
    "danger":      "#e03131",
    "line":        "#eceef3",
    "hover":       "#f2f4f8",
    "log_bg":      "#0f172a",
    "log_text":    "#d7e0f0",
}


def stylesheet() -> str:
    p = PALETTE
    return f"""
* {{
    font-family: {FONT_STACK};
    font-size: 12px;
    color: {p['text']};
}}

#root {{
    background: {p['page']};
    border: 1px solid {p['card_border']};
    border-radius: 14px;
}}
#root[maximized="true"] {{ border-radius: 0px; border: none; }}

/* ── 타이틀바 ─────────────────────────────────────────── */
#titleBar {{ background: transparent; }}
#appTitle  {{ font-size: 14px; font-weight: 800; }}
#appVersion {{ color: {p['text_muted']}; font-size: 11px; }}
#clockLabel {{ color: {p['text_sub']}; font-size: 11px; }}
#statusLabel {{ color: {p['text_sub']}; font-size: 11px; }}

QPushButton#winBtn {{
    background: transparent; border: none; border-radius: 6px;
    color: {p['text_sub']}; font-size: 13px; padding: 0px;
}}
QPushButton#winBtn:hover {{ background: {p['hover']}; }}
QPushButton#winBtn[danger="true"]:hover {{ background: {p['danger']}; color: white; }}

/* ── 탭 ──────────────────────────────────────────────── */
#tabStrip {{ background: transparent; }}
QPushButton#tabBtn {{
    background: transparent; border: none; padding: 8px 6px;
    color: {p['text_muted']}; font-size: 13px; font-weight: 700;
    border-bottom: 2px solid transparent;
}}
QPushButton#tabBtn:hover {{ color: {p['text_sub']}; }}
QPushButton#tabBtn:checked {{
    color: {p['text']}; border-bottom: 2px solid {p['primary']};
}}

/* ── 카드 ────────────────────────────────────────────── */
#card {{
    background: {p['card']};
    border: 1px solid {p['card_border']};
    border-radius: 12px;
}}
#cardTitle {{ font-size: 12.5px; font-weight: 800; }}
#cardBadge {{ color: {p['text_muted']}; font-size: 11px; }}
#sectionLabel {{ color: {p['text_sub']}; font-size: 11.5px; }}
#hintLabel {{ color: {p['text_muted']}; font-size: 11px; }}
#emptyLabel {{ color: {p['text_muted']}; font-size: 11.5px; }}

/* ── 버튼 ────────────────────────────────────────────── */
QPushButton {{
    background: {p['card']};
    border: 1px solid {p['card_border']};
    border-radius: 8px;
    padding: 7px 10px;
    color: {p['text_sub']};
    font-size: 11.5px;
}}
QPushButton:hover  {{ background: {p['hover']}; color: {p['text']}; }}
QPushButton:pressed {{ background: #e9ecf3; }}
QPushButton:disabled {{ color: #c3c8d2; background: #fafbfc; }}

QPushButton[variant="primary"] {{
    background: {p['primary']}; border: 1px solid {p['primary']};
    color: white; font-weight: 700;
}}
QPushButton[variant="primary"]:hover {{ background: {p['primary_dk']}; }}
QPushButton[variant="danger"] {{ color: {p['danger']}; }}
QPushButton[variant="danger"]:hover {{ background: #fff0f0; }}

QPushButton#ctaBtn {{
    background: {p['accent']};
    border: 1px solid {p['accent_dk']};
    border-radius: 10px;
    color: #3b2f00;
    font-size: 14px;
    font-weight: 800;
    padding: 12px;
}}
QPushButton#ctaBtn:hover {{ background: {p['accent_dk']}; }}
QPushButton#ctaBtn[running="true"] {{
    background: {p['danger']}; border: 1px solid {p['danger']}; color: white;
}}
QPushButton#ctaBtn[running="true"]:hover {{ background: #c92a2a; }}

/* 모드 선택 버튼 */
QPushButton#modeBtn {{
    text-align: left; padding: 9px 11px; border-radius: 9px;
    color: {p['text_sub']}; font-size: 11.5px;
}}
QPushButton#modeBtn:checked {{
    background: {p['primary_lt']};
    border: 1px solid {p['primary']};
    color: {p['primary_dk']};
    font-weight: 800;
}}

/* ── 입력 위젯 ───────────────────────────────────────── */
QLineEdit, QSpinBox, QTimeEdit, QDateEdit, QComboBox {{
    background: {p['card']};
    border: 1px solid {p['card_border']};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {p['primary']};
    selection-color: white;
}}
QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus, QDateEdit:focus, QComboBox:focus {{
    border: 1px solid {p['primary']};
}}
QLineEdit::placeholder {{ color: {p['text_muted']}; }}
QSpinBox::up-button, QSpinBox::down-button,
QTimeEdit::up-button, QTimeEdit::down-button,
QDateEdit::up-button, QDateEdit::down-button {{ width: 14px; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {p['card']}; border: 1px solid {p['card_border']};
    selection-background-color: {p['primary_lt']};
    selection-color: {p['text']};
    outline: none;
}}

QCheckBox {{ spacing: 7px; color: {p['text_sub']}; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid #c8cddb; background: white;
}}
QCheckBox::indicator:checked {{
    background: {p['primary']}; border: 1px solid {p['primary']};
    image: none;
}}

/* ── 리스트 / 로그 ───────────────────────────────────── */
QListWidget {{
    background: transparent; border: none; outline: none;
}}
QListWidget::item {{ border: none; padding: 0px; }}
QListWidget::item:selected {{ background: transparent; }}

QPlainTextEdit#logView {{
    background: {p['log_bg']};
    border: 1px solid #16233f;
    border-radius: 10px;
    color: {p['log_text']};
    font-family: {MONO_STACK};
    font-size: 11.5px;
    padding: 10px;
    selection-background-color: #2b4a8a;
}}

QPlainTextEdit#miniLog {{
    background: #fbfcfe;
    border: 1px solid {p['card_border']};
    border-radius: 10px;
    color: {p['text_sub']};
    font-family: {MONO_STACK};
    font-size: 11px;
    padding: 8px;
}}

QProgressBar {{
    background: {p['line']}; border: none; border-radius: 5px;
    height: 6px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {p['primary']}; border-radius: 5px; }}

/* ── 스크롤바 ────────────────────────────────────────── */
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #d3d8e2; border-radius: 4px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: #b9c0ce; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #d3d8e2; border-radius: 4px; min-width: 24px; }}

QToolTip {{
    background: #232a36; color: #f2f4f8; border: none;
    padding: 6px 8px; border-radius: 6px;
}}

#dialogRoot {{ background: {p['page']}; }}
"""
