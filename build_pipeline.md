# CK3 Dynasty Simulator - Build Pipeline

This guide explains how to freeze the Python FastAPI backend into a standalone executable using PyInstaller, and how to bundle it with the React frontend using Tauri's Sidecar feature.

## Prerequisites
1. Python 3.12+
2. Node.js & npm
3. Rust & Cargo (Tauri prerequisites)

## Step 1: Freeze the Python Backend
We use PyInstaller to compile the FastAPI application into a single executable.

```bash
cd backend
pip install -r requirements.txt
pip install pyinstaller

# Build the standalone executable
pyinstaller --name ck3-engine --onefile main.py
```

This will generate an executable in `backend/dist/ck3-engine` (or `ck3-engine.exe` on Windows).

## Step 2: Prepare the Tauri Sidecar
Tauri requires sidecar binaries to be placed in a specific directory and named with the target triple (e.g., `x86_64-pc-windows-msvc`, `x86_64-apple-darwin`, `x86_64-unknown-linux-gnu`).

1. Create the `bin` directory in `src-tauri`:
   ```bash
   mkdir -p src-tauri/bin
   ```
2. Copy the PyInstaller executable to this directory and append your target triple. For example, on Windows:
   ```bash
   cp backend/dist/ck3-engine.exe src-tauri/bin/ck3-engine-x86_64-pc-windows-msvc.exe
   ```

## Step 3: Configure Tauri
Ensure your `src-tauri/tauri.conf.json` includes the sidecar configuration:
```json
{
  "tauri": {
    "bundle": {
      "externalBin": ["bin/ck3-engine"]
    }
  }
}
```

## Step 4: Build the Final Application
Now, build the Tauri application. Tauri will automatically bundle the React frontend and the Python sidecar into a single installer.

```bash
npm run tauri build
```

The final installer (e.g., `.msi` on Windows, `.dmg` on macOS, `.AppImage` on Linux) will be located in `src-tauri/target/release/bundle/`.
