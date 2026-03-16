"""
Centralised path constants for the CK3 Character History Generator.

All output directories are resolved relative to PROJECT_ROOT so that the
application works correctly regardless of the working directory — whether
launched via the CLI, the FastAPI dev server, or a packaged Tauri sidecar.
"""

from __future__ import annotations

import sys
from pathlib import Path
import os


def _find_project_root() -> Path:
    """
    Resolve the project root at import time.

    - In a PyInstaller onefile bundle, sys._MEIPASS is the extraction directory
      which contains all bundled resources.
    - In normal use, the project root is two levels up from this file
      (ck3gen/paths.py → ck3gen/ → project root).
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent.parent


# ── Root ──────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(os.getcwd())

# ── Input directories ─────────────────────────────────────────────────────────

CONFIG_DIR = ROOT_DIR / "config"
FALLBACK_CONFIG_DIR = CONFIG_DIR / "fallback_config_files"
NAME_LISTS_DIR = ROOT_DIR / "name_lists"

# ── Output directories ────────────────────────────────────────────────────────

CHARACTER_OUTPUT_DIR = ROOT_DIR / "Character and Title files"
TREE_OUTPUT_DIR = ROOT_DIR / "Dynasty Preview"