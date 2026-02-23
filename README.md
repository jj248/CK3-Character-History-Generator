# CK3 Character History Generator

A tool for generating character history files for Crusader Kings III (CK3), supporting custom characters, dynasties, and family trees for modding purposes. Available as a desktop GUI (Tauri + React) or a headless CLI.

---

## Features

- **Character Generation** — Automates character entries with customizable attributes
- **Dynasty Creation** — Links characters through familial relationships across generations
- **Name Lists** — Configurable culturally appropriate name assignment
- **Family Trees** — Generates and visualises interconnected family structures
- **Desktop GUI** — Tauri-based app with live config editing, SSE log streaming, and tree image viewer
- **Headless CLI** — Run simulations directly from the terminal without the UI

---

## Project Structure

```
CK3-Character-History-Generator/
├── ck3gen/               # Core Python package (character, simulation, family tree, etc.)
├── api/                  # FastAPI backend — config CRUD, simulation runner, image serving
├── ui/                   # Tauri + React frontend
│   ├── src/              # React/TypeScript source (components, api.ts)
│   └── src-tauri/        # Rust/Tauri shell (sidecar launcher, window config)
├── config/               # JSON config files (initialization, life_stages, skills_and_traits)
├── name_lists/           # Name list files
├── main.py               # Headless CLI entry point
└── requirements.txt      # Python dependencies
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Rust + Cargo | latest stable |
| Tauri CLI | v2 (installed via npm) |

Install system Graphviz (required for family tree rendering):
- **Windows:** `winget install graphviz` or download from https://graphviz.org/download/
- **macOS:** `brew install graphviz`
- **Linux:** `sudo apt install graphviz`

---

## Getting Started (Development)

### 1. Install dependencies

```bash
make install
# or manually:
pip install -r requirements.txt
cd ui && npm install
```

### 2. Run in dev mode

```bash
make dev
```

This starts:
- The FastAPI backend on `http://127.0.0.1:8000` (with `--reload`)
- The Tauri dev window (Vite on `http://localhost:5173`, proxied to the backend)

**Windows (no `make`):** double-click `run_ui.bat`

---

## Headless CLI

Run a simulation without the GUI:

```bash
python main.py
```

Output files are written to `Dynasty Preview/`.

---

## Building a Release `.exe`

```bash
make build
```

This will:
1. Bundle the FastAPI server into a standalone `api_server` binary via PyInstaller
2. Copy the binary into `ui/src-tauri/binaries/`
3. Build the Tauri app (installer + `.exe`) via `npm run tauri build`

The packaged app automatically spawns the `api_server` sidecar on launch — no Python installation required on the end user's machine.

---

## Publishing a Release

Releases are automated via GitHub Actions. Tagging a commit with a `v*` version tag triggers the workflow:

```bash
make release VERSION=v1.2.3
# or manually:
git tag v1.2.3 && git push origin v1.2.3
```

The workflow builds the Windows `.exe` installer and publishes it as a GitHub Release automatically.

---

## Configuration

Config files live in `config/`. They can be edited directly or via the GUI's settings tabs. Fallback defaults are stored in `config/fallback_config_files/`.

| File | Purpose |
|------|---------|
| `initialization.json` | Dynasty definitions, simulation date range, event settings |
| `life_stages.json` | Mortality, marriage, fertility rates by age |
| `skills_and_traits.json` | Trait and skill assignment rules |

---

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

MIT License — see `LICENSE` for details.