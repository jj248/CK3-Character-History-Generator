@echo off
cd /d "%~dp0"

:: ─────────────────────────────────────────────────────────────────────────────
::  CK3 Character History Generator — Development Launcher
::
::  This script:
::    1. Creates / activates a Python venv in the repo root
::    2. Installs Python dependencies
::    3. Starts the FastAPI backend (uvicorn) in a background window
::    4. Launches the Tauri + Vite dev UI from the ui/ folder
::
::  For a RELEASE BUILD (packaged installer) you must:
::    a. Compile the Python backend:
::         pyinstaller api/main.py --onefile --name api_server
::         copy dist\api_server.exe ui\src-tauri\binaries\api_server-x86_64-pc-windows-msvc.exe
::    b. Restore bundle fields in tauri.conf.json from tauri.conf.release.json
::    c. Run: cd ui && npm run tauri build
:: ─────────────────────────────────────────────────────────────────────────────

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

:: ── Start the FastAPI backend in the background ───────────────────────────────
::  Launched from the repo root so that "api.main" and "ck3gen.*" resolve correctly.
echo Starting FastAPI backend on http://127.0.0.1:8000 ...
start "CK3 API Server" /min cmd /c "cd /d "%~dp0" && call venv\Scripts\activate.bat && uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

:: Give uvicorn a moment to bind the port before Tauri proxies requests to it
timeout /t 3 /nobreak >nul

:: ── Launch the Tauri + Vite dev UI ───────────────────────────────────────────
::  Must run from the ui\ folder where package.json lives.
echo Starting Tauri dev UI...
cd ui
npm run tauri dev

:: When Tauri exits, close the background API Server window manually.
pause