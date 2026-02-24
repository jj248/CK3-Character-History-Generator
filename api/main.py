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
#  Path setup — ensures project root is importable in dev and when frozen
# ---------------------------------------------------------------------------

# When frozen by PyInstaller, sys._MEIPASS is the temp extraction directory.
# In dev, the project root is two levels up from api/main.py.
if getattr(sys, "frozen", False):
    _project_root = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _project_root = Path(__file__).parent.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import the CLI runner — single source of truth for the simulation pipeline.
from main import run_main  # noqa: E402
from api.models import InitializationConfig, LifeStagesConfig
from ck3gen.paths import CONFIG_DIR, FALLBACK_CONFIG_DIR, TREE_OUTPUT_DIR

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
def get_initialization() -> InitializationConfig:
    return _read_json(CONFIG_DIR / "initialization.json")


@app.put("/config/initialization")
def put_initialization(body: InitializationConfig) -> dict[str, str]:
    _write_json(CONFIG_DIR / "initialization.json", body.model_dump(mode="json"))
    return {"status": "saved"}


@app.post("/config/initialization/reset")
def reset_initialization() -> dict[str, str]:
    src = FALLBACK_CONFIG_DIR / "initialization.json"
    dst = CONFIG_DIR / "initialization.json"
    if not src.exists():
        raise HTTPException(status_code=404, detail="Fallback initialization config not found")
    shutil.copy2(src, dst)
    return {"status": "reset"}


@app.post("/config/initialization/set-fallback")
def set_initialization_fallback() -> dict[str, str]:
    src = CONFIG_DIR / "initialization.json"
    dst = FALLBACK_CONFIG_DIR / "initialization.json"
    if not src.exists():
        raise HTTPException(status_code=404, detail="Active initialization config not found")
    shutil.copy2(src, dst)
    return {"status": "fallback updated"}


# ---------------------------------------------------------------------------
#  Life stages config endpoints
# ---------------------------------------------------------------------------


@app.get("/config/life-stages")
def get_life_stages() -> LifeStagesConfig:
    return _read_json(CONFIG_DIR / "life_stages.json")


@app.get("/config/life-stages/fallback")
def get_life_stages_fallback() -> LifeStagesConfig:
    return _read_json(FALLBACK_CONFIG_DIR / "life_stages.json")


@app.put("/config/life-stages")
def put_life_stages(body: LifeStagesConfig) -> dict[str, str]:
    _write_json(CONFIG_DIR / "life_stages.json", body.model_dump(mode="json"))
    return {"status": "saved"}


@app.post("/config/life-stages/reset")
def reset_life_stages() -> dict[str, str]:
    src = FALLBACK_CONFIG_DIR / "life_stages.json"
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
    if not TREE_OUTPUT_DIR.exists():
        return []
    return sorted(p.name for p in TREE_OUTPUT_DIR.glob("family_tree_*.png"))


@app.get("/images/{filename}")
def get_image(filename: str) -> FileResponse:
    if not filename.startswith("family_tree_") or not filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Invalid image filename")
    path = TREE_OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/png")


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")