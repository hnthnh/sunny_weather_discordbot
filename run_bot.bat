@echo off
setlocal enabledelayedexpansion

REM Create virtual environment if it does not exist
if not exist .venv (
    echo Creating virtual environment...
    py -m venv .venv || python -m venv .venv
)

REM Activate virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Failed to activate virtual environment. Make sure Python is installed.
    exit /b 1
)

REM Install dependencies
pip install --upgrade pip >nul
pip install -r requirements.txt

REM Run the bot
python bot.py
pause