# Distribution Guide: Packaging the Python Sidecar for Tauri

To distribute your Tauri application with the FastAPI backend, you must compile the Python code into a standalone executable. Tauri will bundle this executable and manage its lifecycle.

## 1. Freezing the Python Backend

You can use either **PyInstaller** or **Nuitka**. PyInstaller is generally easier to set up, while Nuitka compiles to C for better performance.

### Using PyInstaller

1. Install PyInstaller in your Python environment:
   ```bash
   pip install pyinstaller
   ```

2. Navigate to the `backend` directory and run PyInstaller:
   ```bash
   cd backend
   pyinstaller --name api --onedir --windowed main.py
   ```
   *Note: We use `--onedir` instead of `--onefile` for faster startup times, which is critical for sidecars. FastAPI can be slow to extract from a single file.*

## 2. Naming the Binary for Tauri

Tauri requires sidecar binaries to be named with their target triple so it knows which binary to bundle for which platform.

1. Create a `binaries` folder inside `src-tauri`:
   ```bash
   mkdir -p src-tauri/binaries
   ```

2. Determine your target triple. You can find this by running `rustc -vV` and looking at the `host` field. Common triples:
   - Windows: `x86_64-pc-windows-msvc`
   - macOS (Intel): `x86_64-apple-darwin`
   - macOS (Apple Silicon): `aarch64-apple-darwin`
   - Linux: `x86_64-unknown-linux-gnu`

3. Rename and move your compiled Python executable into the `binaries` folder.
   - **Windows Example**: Rename `api.exe` to `api-x86_64-pc-windows-msvc.exe`
   - **macOS Example**: Rename `api` to `api-aarch64-apple-darwin`

   ```bash
   # Example for Windows
   cp backend/dist/api/api.exe src-tauri/binaries/api-x86_64-pc-windows-msvc.exe
   ```

## 3. Tauri Configuration

Ensure your `src-tauri/tauri.conf.json` has the `externalBin` array configured correctly. You only need to specify the base name (`api`), and Tauri will automatically append the target triple during the build process.

```json
"tauri": {
  "bundle": {
    "externalBin": [
      "binaries/api"
    ]
  }
}
```

## 4. Build the Application

Now you can build your Tauri application normally. Tauri will bundle the correct sidecar binary into the final installer.

```bash
npm run tauri build
```
