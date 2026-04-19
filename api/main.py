"""
CK3 Character History Generator — FastAPI backend.
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import shutil
import sys
import os
import threading
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

# ---------------------------------------------------------------------------
#  Path setup — MUST happen before importing project modules
# ---------------------------------------------------------------------------

if getattr(sys, "frozen", False):
    _project_root = Path(sys._MEIPASS) 
else:
    _project_root = Path(__file__).parent.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import the setter first and call it immediately
from ck3gen.paths import set_project_root
set_project_root(_project_root)

# Now it is safe to import local modules that depend on these paths
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
#  Endpoints
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
        raise HTTPException(status_code=404, detail="Fallback config not found")
    shutil.copy2(src, dst)
    return {"status": "reset"}

@app.get("/config/life-stages")
def get_life_stages() -> LifeStagesConfig:
    return _read_json(CONFIG_DIR / "life_stages.json")

@app.put("/config/life-stages")
def put_life_stages(body: LifeStagesConfig) -> dict[str, str]:
    _write_json(CONFIG_DIR / "life_stages.json", body.model_dump(mode="json"))
    return {"status": "saved"}

# ---------------------------------------------------------------------------
#  Simulation & Images
# ---------------------------------------------------------------------------

class _QueueHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[str | None]) -> None:
        super().__init__()
        self._queue = log_queue
    def emit(self, record: logging.LogRecord) -> None:
        self._queue.put(self.format(record))

async def _stream_simulation() -> AsyncGenerator[str, None]:
    log_queue: queue.Queue[str | None] = queue.Queue()
    handler = _QueueHandler(log_queue)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    exception_holder: list[Exception] = []

    def _run() -> None:
        try:
            run_main()
        except Exception as exc:
            exception_holder.append(exc)
        finally:
            log_queue.put(None)

    threading.Thread(target=_run, daemon=True).start()

    while True:
        try:
            message = log_queue.get(timeout=0.05)
            if message is None: break
            yield f"data: {json.dumps({'log': message})}\n\n"
        except queue.Empty:
            await asyncio.sleep(0)

    logging.getLogger().removeHandler(handler)
    if exception_holder:
        yield f"data: {json.dumps({'error': str(exception_holder[0])})}\n\n"
    else:
        yield f"data: {json.dumps({'status': 'complete'})}\n\n"

@app.post("/simulation/run")
def run_simulation() -> StreamingResponse:
    return StreamingResponse(_stream_simulation(), media_type="text/event-stream")

@app.get("/images")
def list_images() -> list[str]:
    if not TREE_OUTPUT_DIR.exists(): return []
    return sorted(p.name for p in TREE_OUTPUT_DIR.glob("family_tree_*.png"))

@app.get("/images/{filename}")
def get_image(filename: str) -> FileResponse:
    path = TREE_OUTPUT_DIR / filename
    if not path.exists(): raise HTTPException(status_code=404)
    return FileResponse(path, media_type="image/png")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")