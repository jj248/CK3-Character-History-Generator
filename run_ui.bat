@echo off
cd /d "%~dp0"

:: Ask if user wants to use a proxy
set /p USE_PROXY=Are you behind a proxy? (y/n): 

if /i "%USE_PROXY%"=="y" (
    set /p PROXY_USER=Enter proxy username: 
    set /p PROXY_PASS=Enter proxy password: 
    set /p PROXY_HOST=Enter proxy server (e.g., proxy.example.com): 
    set /p PROXY_PORT=Enter proxy port (e.g., 8080): 
    set "PROXY_URL=http://%PROXY_USER%:%PROXY_PASS%@%PROXY_HOST%:%PROXY_PORT%"
)

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate the virtual environment
call venv\Scripts\activate.bat

:: Install dependencies
if /i "%USE_PROXY%"=="y" (
    pip install --proxy %PROXY_URL% -r requirements.txt
) else (
    pip install -r requirements.txt
)

:: Run the app
streamlit run .\interface\ui_app.py
pause
