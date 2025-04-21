@echo off
cd /d "%~dp0"

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate it
call venv\Scripts\activate.bat

:: Install dependencies if needed
pip install -r requirements.txt

:: Run the app
streamlit run .\interface\ui_app.py
pause