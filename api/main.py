"""
CK3 Character History Generator — FastAPI backend.

Dev:        uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
Packaged:   run as a PyInstaller sidecar spawned by the Tauri shell
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import shutil
import sys
import threading
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

# ---------------------------------------------------------------------------
#  Path setup — works both in dev (repo root) and as a PyInstaller onefile
# ---------------------------------------------------------------------------

# When frozen by PyInstaller, sys._MEIPASS is the temp extraction directory.
# In dev, we just use the repo root (two levels up from api/main.py).
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    PROJECT_ROOT = Path(__file__).parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the CLI runner — this is the single source of truth for the pipeline.
from main import run_main  # noqa: E402

# ---------------------------------------------------------------------------
#  App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="CK3 Character History Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_DIR = PROJECT_ROOT / "config"
FALLBACK_DIR = CONFIG_DIR / "fallback_config_files"
OUTPUT_DIR = PROJECT_ROOT / "Dynasty Preview"

# ---------------------------------------------------------------------------
#  Config helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Config file not found: {path.name}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ---------------------------------------------------------------------------
#  Initialization config endpoints
# ---------------------------------------------------------------------------


@app.get("/config/initialization")
def get_initialization() -> dict:
    return _read_json(CONFIG_DIR / "initialization.json")


@app.put("/config/initialization")
def put_initialization(body: dict) -> dict[str, str]:
    _write_json(CONFIG_DIR / "initialization.json", body)
    return {"status": "saved"}


@app.post("/config/initialization/reset")
def reset_initialization() -> dict[str, str]:
    src = FALLBACK_DIR / "initialization.json"
    dst = CONFIG_DIR / "initialization.json"
    if not src.exists():
        raise HTTPException(status_code=404, detail="Fallback initialization config not found")
    shutil.copy2(src, dst)
    return {"status": "reset"}


@app.post("/config/initialization/set-fallback")
def set_initialization_fallback() -> dict[str, str]:
    src = CONFIG_DIR / "initialization.json"
    dst = FALLBACK_DIR / "initialization.json"
    if not src.exists():
        raise HTTPException(status_code=404, detail="Active initialization config not found")
    shutil.copy2(src, dst)
    return {"status": "fallback updated"}


# ---------------------------------------------------------------------------
#  Life stages config endpoints
# ---------------------------------------------------------------------------


@app.get("/config/life-stages")
def get_life_stages() -> dict:
    return _read_json(CONFIG_DIR / "life_stages.json")


@app.get("/config/life-stages/fallback")
def get_life_stages_fallback() -> dict:
    return _read_json(FALLBACK_DIR / "life_stages.json")


@app.put("/config/life-stages")
def put_life_stages(body: dict) -> dict[str, str]:
    _write_json(CONFIG_DIR / "life_stages.json", body)
    return {"status": "saved"}


@app.post("/config/life-stages/reset")
def reset_life_stages() -> dict[str, str]:
    src = FALLBACK_DIR / "life_stages.json"
    dst = CONFIG_DIR / "life_stages.json"
    if not src.exists():
        raise HTTPException(status_code=404, detail="Fallback life stages config not found")
    shutil.copy2(src, dst)
    return {"status": "reset"}


# ---------------------------------------------------------------------------
#  Simulation — SSE log streaming
# ---------------------------------------------------------------------------


class _QueueHandler(logging.Handler):
    """Forwards log records into a thread-safe queue for SSE streaming."""

    def __init__(self, log_queue: queue.Queue[str | None]) -> None:
        super().__init__()
        self._queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        self._queue.put(self.format(record))


async def _stream_simulation() -> AsyncGenerator[str, None]:
    """Run the simulation in a background thread, yield SSE-formatted log lines."""
    log_queue: queue.Queue[str | None] = queue.Queue()
    handler = _QueueHandler(log_queue)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    exception_holder: list[Exception] = []

    def _run() -> None:
        try:
            run_main()
        except Exception as exc:  # noqa: BLE001
            exception_holder.append(exc)
        finally:
            log_queue.put(None)  # sentinel — signals stream end

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    try:
        while True:
            try:
                message = log_queue.get(timeout=0.05)
            except queue.Empty:
                await asyncio.sleep(0)
                continue

            if message is None:
                break

            yield f"data: {json.dumps({'log': message})}\n\n"
            await asyncio.sleep(0)
    finally:
        root_logger.removeHandler(handler)

    thread.join(timeout=5)

    if exception_holder:
        yield f"data: {json.dumps({'error': str(exception_holder[0])})}\n\n"
    else:
        yield f"data: {json.dumps({'status': 'complete'})}\n\n"


@app.post("/simulation/run")
def run_simulation() -> StreamingResponse:
    return StreamingResponse(
        _stream_simulation(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
#  Dynasty tree image endpoints
# ---------------------------------------------------------------------------


@app.get("/images")
def list_images() -> list[str]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted(p.name for p in OUTPUT_DIR.glob("family_tree_*.png"))


@app.get("/images/{filename}")
def get_image(filename: str) -> FileResponse:
    if not filename.startswith("family_tree_") or not filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Invalid image filename")
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/png")


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")