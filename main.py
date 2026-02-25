"""
main.py — CK3 Character History Generator headless CLI entry point.

Run directly:
    python main.py

Also imported by api/main.py to power the /simulation/run SSE endpoint:
    from main import run_main

Full pipeline per run:
  1. Generate dynasty definition + localisation files
  2. Run the year-by-year simulation
  3. Export character history  →  Character and Title files/family_history.txt
  4. Build and write title histories  →  Character and Title files/title_history.txt
  5. Render Graphviz family tree images  →  Dynasty Preview/
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path whether this file is run directly or
# imported by the api/main.py sidecar.
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ck3gen.config_loader import ConfigLoader, NUM_SIMULATIONS
from ck3gen.dynasty_creation import (
    generate_dynasty_definitions,
    generate_dynasty_name_localization,
    generate_dynasty_motto_localization,
)
from ck3gen.name_loader import NameLoader
from ck3gen.paths import CHARACTER_OUTPUT_DIR, CONFIG_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)


def run_main() -> None:
    """Load config, run all simulation(s), and write every output file."""
    config_loader = ConfigLoader(config_folder=CONFIG_DIR)
    config = config_loader.config

    # NameLoader takes a folder path, not the config dict.
    name_loader = NameLoader(name_list_folder=str(PROJECT_ROOT / "name_lists"))

    # Write CK3 dynasty definition + localisation files once, before simulating.
    config_file = CONFIG_DIR / "initialization.json"
    generate_dynasty_definitions(config_file)
    generate_dynasty_name_localization(config_file)
    generate_dynasty_motto_localization(config_file)

    for i in range(NUM_SIMULATIONS):
        if NUM_SIMULATIONS > 1:
            logging.info("── Simulation %d / %d ──", i + 1, NUM_SIMULATIONS)

        # ── 1. Simulate ───────────────────────────────────────────────────────
        from ck3gen.simulation import Simulation  # noqa: PLC0415
        simulation = Simulation(config, name_loader)
        simulation.run_simulation()

        # ── 2. Export character history ───────────────────────────────────────
        simulation.export_characters()

        # ── 3. Title histories ────────────────────────────────────────────────
        _run_title_history(config_file)

        # ── 4. Family tree images ─────────────────────────────────────────────
        _run_family_trees(config)

    logging.info("Done. Output written to '%s'.", CHARACTER_OUTPUT_DIR)


# ---------------------------------------------------------------------------
#  Pipeline helpers
# ---------------------------------------------------------------------------

def _run_title_history(config_file: Path) -> None:
    """Parse the exported character file and write title_history.txt."""
    from ck3gen.title_history import CharacterLoader, TitleHistory  # noqa: PLC0415

    character_file = CHARACTER_OUTPUT_DIR / "family_history.txt"
    if not character_file.exists():
        logging.warning("family_history.txt not found — skipping title history.")
        return

    loader = CharacterLoader()
    loader.load_characters(str(character_file))

    history = TitleHistory(loader, str(config_file))
    history.build_title_histories()
    history.write_title_histories_to_file()


def _run_family_trees(config: dict) -> None:
    """Build and render Graphviz family tree images."""
    from ck3gen.family_tree import FamilyTree  # noqa: PLC0415

    character_file = CHARACTER_OUTPUT_DIR / "family_history.txt"
    title_file     = CHARACTER_OUTPUT_DIR / "title_history.txt"

    if not character_file.exists():
        logging.warning("family_history.txt not found — skipping family trees.")
        return

    tree = FamilyTree(str(character_file), str(title_file), config)
    tree.build_trees()
    tree.render_trees()


if __name__ == "__main__":
    run_main()