"""
Centralised path constants for the CK3 Character History Generator.

All output directories are resolved relative to PROJECT_ROOT so that the
application works correctly regardless of the working directory — whether
launched via the CLI, the FastAPI dev server, or a packaged Tauri sidecar.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

def _find_project_root() -> Path:
    """
    Resolve the project root at import time.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


# ── Internal Base ────────────────────────────────────────────────────────────
PROJECT_ROOT = _find_project_root()

# ── Global Path Variables ─────────────────────────────────────────────────────
# These are updated via set_project_root() in api/main.py
CONFIG_DIR = PROJECT_ROOT / "config"
FALLBACK_CONFIG_DIR = CONFIG_DIR / "fallback_config_files"
NAME_LISTS_DIR = PROJECT_ROOT / "name_lists"

# Output directories default to PROJECT_ROOT for dev mode
CHARACTER_OUTPUT_DIR = PROJECT_ROOT / "Character and Title files"
TREE_OUTPUT_DIR = PROJECT_ROOT / "Dynasty Preview"

def set_project_root(new_root: Path):
    """
    Updates all path constants. When frozen, redirects writable outputs 
    to the User's Documents folder to avoid Permission Errors.
    """
    global PROJECT_ROOT, CONFIG_DIR, FALLBACK_CONFIG_DIR, NAME_LISTS_DIR
    global CHARACTER_OUTPUT_DIR, TREE_OUTPUT_DIR

    PROJECT_ROOT = new_root
    CONFIG_DIR = PROJECT_ROOT / "config"
    FALLBACK_CONFIG_DIR = CONFIG_DIR / "fallback_config_files"
    NAME_LISTS_DIR = PROJECT_ROOT / "name_lists"

    if getattr(sys, "frozen", False):
        # Redirect outputs to Documents/CK3 Character Generator
        user_docs = Path(os.path.expanduser("~")) / "Documents" / "CK3 Character Generator"
        CHARACTER_OUTPUT_DIR = user_docs / "Character and Title files"
        TREE_OUTPUT_DIR = user_docs / "Dynasty Preview"
    else:
        CHARACTER_OUTPUT_DIR = PROJECT_ROOT / "Character and Title files"
        TREE_OUTPUT_DIR = PROJECT_ROOT / "Dynasty Preview"

    # Ensure output directories exist
    CHARACTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TREE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Simulation Constants ──────────────────────────────────────────────────────
NUM_SIMULATIONS = 1