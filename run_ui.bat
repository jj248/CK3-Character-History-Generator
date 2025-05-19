@echo off
cd /d "%~dp0"

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate the virtual environment
call venv\Scripts\activate.bat

:: Install dependencies
pip install -r requirements.txt

:: Run the app
streamlit run .\interface\ui_app.py
pause
