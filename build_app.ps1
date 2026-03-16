# build_app.ps1
# CK3 Character History Generator -- Tauri release build script.
#
# Usage:
#   .\build_app.ps1            # Full release build
#   .\build_app.ps1 -Debug     # Debug build: sidecar keeps its console window open
#                              # so you can see Python errors on startup
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
#  Helper
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
    # No --noconsole / --windowed means the sidecar keeps its console open.
} else {
    $pyinstallerArgs += "--noconsole"
}

& "$ProjectRoot\venv\Scripts\pyinstaller.exe" @pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    Die "PyInstaller failed. Check output above."
}

# ---------------------------------------------------------------------------
#  Step 3: Copy the compiled sidecar into the Tauri binaries directory
# ---------------------------------------------------------------------------

Step "Copying sidecar binary into Tauri bundle"

$sidecarSrc = "$ProjectRoot\dist\api_server.exe"
$sidecarDst = "$ProjectRoot\ui\src-tauri\binaries\api_server-x86_64-pc-windows-msvc.exe"

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

$tauriConfSrc     = "$ProjectRoot\ui\src-tauri\tauri.conf.release.json"
$tauriConfDst     = "$ProjectRoot\ui\src-tauri\tauri.conf.json"
$tauriConfBackup  = "$ProjectRoot\ui\src-tauri\tauri.conf.dev.json"

if (Test-Path $tauriConfSrc) {
    # Back up the dev config so it can be restored after the build.
    if (Test-Path $tauriConfDst) {
        Copy-Item $tauriConfDst $tauriConfBackup -Force
    }
    Copy-Item $tauriConfSrc $tauriConfDst -Force
    Write-Host "  Release tauri.conf.json applied (dev config backed up to tauri.conf.dev.json)"
} else {
    Write-Host "  No tauri.conf.release.json found -- using existing tauri.conf.json"
}

# ---------------------------------------------------------------------------
#  Step 5: npm install (if node_modules is absent)
# ---------------------------------------------------------------------------

Step "Installing Node.js dependencies"

if (-not (Test-Path "$ProjectRoot\ui\node_modules")) {
    Push-Location "$ProjectRoot\ui"
    npm install
    Pop-Location
}

# ---------------------------------------------------------------------------
#  Step 6: Tauri release build
# ---------------------------------------------------------------------------

Step "Building Tauri release bundle"

Push-Location "$ProjectRoot\ui"
npm run tauri build
$tauriBuildExit = $LASTEXITCODE
Pop-Location

# ---------------------------------------------------------------------------
#  Step 7: Restore dev tauri.conf.json
# ---------------------------------------------------------------------------

if (Test-Path $tauriConfBackup) {
    Copy-Item $tauriConfBackup $tauriConfDst -Force
    Remove-Item $tauriConfBackup -Force
    Write-Host ""
    Write-Host "  Dev tauri.conf.json restored."
}

if ($tauriBuildExit -ne 0) {
    Die "Tauri build failed. Check output above."
}

# ---------------------------------------------------------------------------
#  Done
# ---------------------------------------------------------------------------

Step "Build complete"
Write-Host ""
Write-Host "Installer: ui\src-tauri\target\release\bundle\msi\" -ForegroundColor Green
Write-Host ""

if ($Debug) {
    Write-Host "DEBUG BUILD NOTE:" -ForegroundColor Yellow
    Write-Host "  The sidecar (api_server.exe) was compiled without --noconsole."
    Write-Host "  When launched from the installed app, a console window will appear"
    Write-Host "  showing the FastAPI/uvicorn startup output and any Python errors."
    Write-Host "  Rebuild without -Debug for a clean release."
    Write-Host ""
}
