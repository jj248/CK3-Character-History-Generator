@echo off
cd /d "%~dp0"

:: -----------------------------------------------------------------------------
::  CK3 Character History Generator -- Development Launcher
::
::  Steps performed by this script:
::    1. Creates and activates a Python venv, installs Python dependencies.
::    2. Runs npm install inside ui\ if node_modules is absent.
::    3. Starts the FastAPI backend (uvicorn) in a minimised background window.
::    4. Launches the Tauri + Vite dev UI from the ui\ folder.
::
::  One-time prerequisites (install manually before first run):
::    - Python 3.11+  https://www.python.org/downloads/
::    - Node.js 18+   https://nodejs.org/
::    - Rust + cargo  https://rustup.rs/
::
::  Release build:
::    a. pyinstaller api/main.py --onefile --name api_server
::       copy dist\api_server.exe ui\src-tauri\binaries\api_server-x86_64-pc-windows-msvc.exe
::    b. copy ui\src-tauri\tauri.conf.release.json ui\src-tauri\tauri.conf.json
::    c. cd ui && npm run tauri build
:: -----------------------------------------------------------------------------

:: ── Python virtual environment ────────────────────────────────────────────────

if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create venv. Is Python 3.11+ installed and on PATH?
        pause & exit /b 1
    )
)

call venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: pip install failed. Check requirements.txt and your network connection.
    pause & exit /b 1
)

:: ── Node.js dependencies ──────────────────────────────────────────────────────

where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not on PATH.
    echo        Download it from https://nodejs.org/ then re-run this script.
    pause & exit /b 1
)

if not exist ui\node_modules (
    echo Installing Node.js dependencies -- this may take a minute on first run...
    pushd ui
    npm install
    if errorlevel 1 (
        echo ERROR: npm install failed. Check your network connection.
        popd & pause & exit /b 1
    )
    popd
)

:: ── FastAPI backend ───────────────────────────────────────────────────────────
::  Launched from the repo root so that "api.main" and "ck3gen.*" resolve correctly.

echo Starting FastAPI backend on http://127.0.0.1:8000 ...
start "CK3 API Server" /min cmd /c "cd /d "%~dp0" && call venv\Scripts\activate.bat && uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

:: Give uvicorn a moment to bind before Tauri starts proxying requests.
timeout /t 3 /nobreak >nul

:: ── Tauri dev UI ─────────────────────────────────────────────────────────────

echo Starting Tauri dev UI...
pushd ui
npm run tauri dev
popd

:: The background API Server window must be closed manually after Tauri exits.
pause