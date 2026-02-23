@echo off
cd /d "%~dp0"

:: ── Python virtual environment ────────────────────────────────────────────────
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install -r requirements.txt

:: ── Node dependencies ─────────────────────────────────────────────────────────
echo Installing Node dependencies...
cd ui
call npm install
cd ..

:: ── Start FastAPI backend in the background ───────────────────────────────────
echo Starting FastAPI backend on http://127.0.0.1:8000 ...
start "CK3Gen API" /B venv\Scripts\uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

:: Give the server a moment to start before the UI connects
timeout /t 2 /nobreak > nul

:: ── Start Tauri dev server ────────────────────────────────────────────────────
echo Starting Tauri dev server...
cd ui
call npm run tauri dev

pause