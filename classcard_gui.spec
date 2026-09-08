# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 스펙 파일 — GUI를 단일 실행 파일(.exe)로 묶는다.

사용법:
    pip install pyinstaller
    pyinstaller --noconfirm --clean classcard_gui.spec
    -> dist/ClasscardAutomation.exe

주의: .env 는 실행 파일에 포함하지 않는다(계정 정보 보호).
      exe 와 같은 폴더에 .env 를 두면 그대로 읽는다.
"""

import os

APP_DIR = os.path.join(os.getcwd(), "Classcard-Automation")

a = Analysis(
    [os.path.join(APP_DIR, "gui.py")],
    pathex=[APP_DIR],
    binaries=[],
    datas=[],
    hiddenimports=[
        "main", "gui_engine", "gui_theme", "gui_widgets", "gui_login", "auth",
        "AutoAll", "HtmlParser", "Matching", "Memorize", "MemorizeSentence",
        "Recall", "RecallSentence", "Scramble", "Spell", "Test", "TestSentence",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ClasscardAutomation",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # 콘솔 창 없이 GUI만 표시
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
