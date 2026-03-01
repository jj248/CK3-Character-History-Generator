@echo off
cd /d "%~dp0"

:: ─────────────────────────────────────────────
::  CK3 Character History Generator — Dev launcher
::  Starts the FastAPI backend (uvicorn) then
::  opens the Tauri / Vite dev front-end.
:: ─────────────────────────────────────────────

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate the virtual environment
call venv\Scripts\activate.bat

:: Install / update Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt --quiet

:: ── Start the FastAPI backend in the background ──────────────────────────────
::  The API file lives at api/main.py and is served on port 8000.
::  We launch it in a new minimised window so its console output stays separate.
echo Starting FastAPI backend on http://127.0.0.1:8000 ...
start "CK3 API Server" /min cmd /c "venv\Scripts\activate.bat && uvicorn api.main:app --host 127.0.0.1 --port 8000"

:: Give uvicorn a moment to bind the port before Tauri tries to proxy it
timeout /t 3 /nobreak >nul

:: ── Launch the Tauri + Vite dev UI ──────────────────────────────────────────
echo Starting Tauri dev UI...
cd ui
npm run tauri dev

:: When Tauri exits, the API server window can be closed manually.
pause