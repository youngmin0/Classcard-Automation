@echo off
chcp 65001 > nul
title 클래스카드 자동화 GUI
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [!] Python을 찾을 수 없습니다. https://www.python.org 에서 설치한 뒤 다시 실행하세요.
    pause
    exit /b 1
)

python -c "import PySide6, selenium, bs4, dotenv" >nul 2>nul
if errorlevel 1 (
    echo [*] 필요한 라이브러리를 설치합니다. 처음 한 번만 시간이 걸립니다...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [!] 라이브러리 설치에 실패했습니다.
        pause
        exit /b 1
    )
)

cd Classcard-Automation
python gui.py
if errorlevel 1 pause
