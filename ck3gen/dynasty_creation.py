"""
Dynasty file generation utilities.

Produces three CK3-compatible output files from the active initialization
config:
  - dynasty_definitions.txt       (dynasty blocks)
  - lotr_dynasty_names_l_english.yml   (name localisation)
  - lotr_mottos_l_english.yml          (motto localisation)

All files are written to CHARACTER_OUTPUT_DIR defined in ck3gen.paths.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ck3gen.paths import CHARACTER_OUTPUT_DIR, CONFIG_DIR

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Internal helpers
# ---------------------------------------------------------------------------


def _load_config(config_file: Path) -> dict | None:
    """Load and return the initialization JSON, or None on failure."""
    try:
        return json.loads(config_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.error("Config file not found: %s", config_file)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse %s: %s", config_file, exc)
    return None


def _ensure_output_dir() -> None:
    CHARACTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------


def generate_dynasty_definitions(
    config_file: Path | str = CONFIG_DIR / "initialization.json",
    output_file: str = "dynasty_definitions.txt",
) -> None:
    """Write CK3 dynasty definition blocks for every dynasty in the config."""
    config_file = Path(config_file)
    config = _load_config(config_file)
    if config is None:
        return

    _ensure_output_dir()
    output_path = CHARACTER_OUTPUT_DIR / output_file

    dynasties = config.get("dynasties", [])
    lines: list[str] = []

    for dynasty in dynasties:
        dynasty_id = dynasty.get("dynastyID", "").replace("dynasty_", "")
        culture_id = dynasty.get("cultureID", "unknown_culture")

        if not dynasty_id:
            logger.warning("Skipping dynasty with missing dynastyID.")
            continue

        lines.append(f"dynasty_{dynasty_id} = {{")
        lines.append(f'\tname = "dynn_{dynasty_id}"')
        lines.append(f'\tculture = "{culture_id}"')
        lines.append(f"\tmotto = dynn_{dynasty_id}_motto")
        lines.append("}\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")

    logger.debug("Dynasty definitions exported to %s.", output_path)


def generate_dynasty_name_localization(
    config_file: Path | str = CONFIG_DIR / "initialization.json",
    output_file: str = "lotr_dynasty_names_l_english.yml",
) -> None:
    """Write CK3 dynasty name localisation entries."""
    config_file = Path(config_file)
    config = _load_config(config_file)
    if config is None:
        return

    _ensure_output_dir()
    output_path = CHARACTER_OUTPUT_DIR / output_file

    dynasties = config.get("dynasties", [])
    lines: list[str] = []

    for dynasty in dynasties:
        dynasty_id = dynasty.get("dynastyID", "").replace("dynasty_", "")
        dynasty_name = dynasty.get("dynastyName", "")

        if not dynasty_name:
            logger.warning("Skipping dynasty with missing dynastyName.")
            continue

        lines.append(f'dynn_{dynasty_id}: "{dynasty_name}"')

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    logger.debug("Dynasty names exported to %s.", output_path)


def generate_dynasty_motto_localization(
    config_file: Path | str = CONFIG_DIR / "initialization.json",
    output_file: str = "lotr_mottos_l_english.yml",
) -> None:
    """Write CK3 dynasty motto localisation entries."""
    config_file = Path(config_file)
    config = _load_config(config_file)
    if config is None:
        return

    _ensure_output_dir()
    output_path = CHARACTER_OUTPUT_DIR / output_file

    dynasties = config.get("dynasties", [])
    lines: list[str] = []

    for dynasty in dynasties:
        dynasty_id = dynasty.get("dynastyID", "").replace("dynasty_", "")
        motto = dynasty.get("dynastyMotto", "")

        if not motto:
            logger.warning("Skipping dynasty with missing dynastyMotto.")
            continue

        lines.append(f'dynn_{dynasty_id}_motto: "{motto}"')

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    logger.debug("Dynasty mottos exported to %s.", output_path)