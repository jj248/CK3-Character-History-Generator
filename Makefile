.PHONY: install-py install-ui install dev build release

# ── Python dependencies ────────────────────────────────────────────────────────
install-py:
	pip install -r requirements.txt

# ── Node / Tauri dependencies ──────────────────────────────────────────────────
install-ui:
	cd ui && npm install

# ── Install everything ─────────────────────────────────────────────────────────
install: install-py install-ui

# ── Development (FastAPI + Tauri dev server, hot-reload) ──────────────────────
dev:
	@echo "Starting FastAPI backend..."
	start /B uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
	@echo "Starting Tauri dev server..."
	cd ui && npm run tauri dev

# ── Production build (PyInstaller sidecar + Tauri bundle) ─────────────────────
build:
	@echo "Building FastAPI sidecar with PyInstaller..."
	pyinstaller --onefile --name api_server api/main.py
	@echo "Copying sidecar to Tauri binaries directory..."
	mkdir -p ui/src-tauri/binaries
	cp dist/api_server* ui/src-tauri/binaries/
	@echo "Building Tauri app..."
	cd ui && npm run tauri build

# ── Headless CLI run (unchanged behaviour) ────────────────────────────────────
run:
	python main.py

# ── Tag a release (triggers GitHub Actions) ───────────────────────────────────
release:
	@test -n "$(VERSION)" || (echo "Usage: make release VERSION=v1.2.3" && exit 1)
	git tag $(VERSION)
	git push origin $(VERSION)