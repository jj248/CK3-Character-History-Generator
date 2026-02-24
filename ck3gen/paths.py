"""
Centralised path constants for the CK3 Character History Generator.

All output directories are resolved relative to PROJECT_ROOT so that the
application works correctly regardless of the working directory — whether
launched via the CLI, the FastAPI dev server, or a packaged Tauri sidecar.
"""

from __future__ import annotations

import sys
from pathlib import Path


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

PROJECT_ROOT: Path = _find_project_root()

# ── Input directories ─────────────────────────────────────────────────────────

CONFIG_DIR: Path = PROJECT_ROOT / "config"
FALLBACK_CONFIG_DIR: Path = CONFIG_DIR / "fallback_config_files"
NAME_LISTS_DIR: Path = PROJECT_ROOT / "name_lists"

# ── Output directories ────────────────────────────────────────────────────────

# Character history, title history, and dynasty definition exports
CHARACTER_OUTPUT_DIR: Path = PROJECT_ROOT / "Character and Title files"

# Rendered family tree PNG images (served by the FastAPI /images endpoint)
TREE_OUTPUT_DIR: Path = PROJECT_ROOT / "Dynasty Preview"