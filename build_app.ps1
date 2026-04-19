# build_app.ps1
# CK3 Character History Generator -- Tauri release build script.
#
# Usage:
#   .\build_app.ps1             # Full release build
#   .\build_app.ps1 -Debug      # Debug build: sidecar keeps its console window open
#                               # so you can see Python errors on startup
#
# Prerequisites (install once):
#   - Python 3.11+   https://www.python.org/downloads/
#   - Node.js 18+    https://nodejs.org/
#   - Rust + cargo   https://rustup.rs/
#   - pip install pyinstaller

param(
    [switch]$Debug
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

function Step([string]$msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Die([string]$msg) {
    Write-Host ""
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
#  Step 0: Prerequisites check
# ---------------------------------------------------------------------------

Step "Checking prerequisites"

foreach ($tool in @("python", "node", "cargo", "pyinstaller")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Die "'$tool' not found on PATH. See script header for install links."
    }
    Write-Host "  $tool ... OK"
}

# ---------------------------------------------------------------------------
#  Step 1: Python venv + dependencies
# ---------------------------------------------------------------------------

Step "Setting up Python virtual environment"

if (-not (Test-Path "$ProjectRoot\venv")) {
    python -m venv "$ProjectRoot\venv"
}

# Ensure dependencies are installed within the venv
& "$ProjectRoot\venv\Scripts\pip.exe" install -r "$ProjectRoot\requirements.txt" --quiet

# ---------------------------------------------------------------------------
#  Step 2: PyInstaller -- compile the FastAPI sidecar
# ---------------------------------------------------------------------------

Step "Compiling FastAPI sidecar with PyInstaller"

$pyinstallerArgs = @(
    "api/main.py",
    "--onefile",
    "--name", "api_server",
    "--paths", $ProjectRoot,
    # CRITICAL: Tell PyInstaller to bundle your local code modules
    "--collect-all", "ck3gen",
    "--collect-all", "utils",
    "--add-data", "$ProjectRoot/config;config",
    "--add-data", "$ProjectRoot/name_lists;name_lists",
    "--collect-data", "fastapi",
    "--hidden-import", "uvicorn.logging",
    "--hidden-import", "uvicorn.protocols.http.h11_impl",
    "--hidden-import", "uvicorn.protocols.http.httptools_impl",
    "--hidden-import", "uvicorn.protocols.websockets.auto",
    "--hidden-import", "uvicorn.lifespan.on",
    "--hidden-import", "uvicorn.lifespan.off"
)

if ($Debug) {
    Write-Host "  [DEBUG] Building with console window visible for sidecar diagnostics"
} else {
    $pyinstallerArgs += "--noconsole"
}

& "$ProjectRoot\venv\Scripts\pyinstaller.exe" @pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    Die "PyInstaller failed. Check output above."
}

# ---------------------------------------------------------------------------
#  Step 3: Copy the compiled sidecar into the Tauri bin directory
# ---------------------------------------------------------------------------

Step "Copying sidecar binary into Tauri bundle"

$sidecarSrc = "$ProjectRoot\dist\api_server.exe"
# CRITICAL: Target directory must match tauri.conf.json (usually 'bin')
$sidecarDst = "$ProjectRoot\ui\src-tauri\bin\api_server-x86_64-pc-windows-msvc.exe"

if (-not (Test-Path $sidecarSrc)) {
    Die "PyInstaller output not found at: $sidecarSrc"
}

$dstDir = Split-Path $sidecarDst -Parent
if (-not (Test-Path $dstDir)) {
    New-Item -ItemType Directory -Path $dstDir | Out-Null
}

Copy-Item -Path $sidecarSrc -Destination $sidecarDst -Force
Write-Host "  Copied to: $sidecarDst"

# ---------------------------------------------------------------------------
#  Step 4: Apply release tauri.conf.json overrides
# ---------------------------------------------------------------------------

Step "Applying release Tauri configuration"

$tauriConfSrc     = "$ProjectRoot\ui\src-tauri\tauri_conf.release.json"
$tauriConfDst     = "$ProjectRoot\ui\src-tauri\tauri.conf.json"
$tauriConfBackup  = "$ProjectRoot\ui\src-tauri\tauri.conf.dev.json"

if (Test-Path $tauriConfSrc) {
    if (Test-Path $tauriConfDst) {
        Copy-Item $tauriConfDst $tauriConfBackup -Force
    }
    Copy-Item $tauriConfSrc $tauriConfDst -Force
    Write-Host "  Release tauri.conf.json applied"
}

# ---------------------------------------------------------------------------
#  Step 5: npm install (if node_modules is absent)
# ---------------------------------------------------------------------------

Step "Installing Node.js dependencies"

if (-not (Test-Path "$ProjectRoot\ui\node_modules")) {
    Push-Location "$ProjectRoot\ui"
    
    # Temporarily disable strict mode to prevent npm.ps1 from crashing
    Set-StrictMode -Off
    npm install
    Set-StrictMode -Version Latest
    
    Pop-Location
}

# ---------------------------------------------------------------------------
#  Step 6: Tauri release build
# ---------------------------------------------------------------------------

Step "Building Tauri release bundle"

Push-Location "$ProjectRoot\ui"

# Temporarily disable strict mode again for the tauri build command
Set-StrictMode -Off
npm run tauri build
$tauriBuildExit = $LASTEXITCODE
Set-StrictMode -Version Latest

Pop-Location

# ---------------------------------------------------------------------------
#  Step 7: Restore dev tauri.conf.json
# ---------------------------------------------------------------------------

if (Test-Path $tauriConfBackup) {
    Copy-Item $tauriConfBackup $tauriConfDst -Force
    Remove-Item $tauriConfBackup -Force
    Write-Host "  Dev tauri.conf.json restored."
}

if ($tauriBuildExit -ne 0) {
    Die "Tauri build failed."
}

# ---------------------------------------------------------------------------
#  Done
# ---------------------------------------------------------------------------

Step "Build complete"
Write-Host "Installer: ui\src-tauri\target\release\bundle\msi\" -ForegroundColor Green