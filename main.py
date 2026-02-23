"""
CK3 Character History Generator — headless CLI entry point.

Run directly:
    python main.py

Also imported by api/main.py to power the /simulation/run endpoint:
    from main import run_main
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so ck3gen and utils are importable
# whether this is run directly or imported by the API sidecar.
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ck3gen.config_loader import ConfigLoader, NUM_SIMULATIONS
from ck3gen.name_loader import NameLoader
from ck3gen.simulation import Simulation
from ck3gen.dynasty_creation import (
    generate_dynasty_definitions,
    generate_dynasty_name_localization,
    generate_dynasty_motto_localization,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)


def run_main() -> None:
    """Load config, run simulation(s), and write all output files."""
    config_loader = ConfigLoader(config_folder="config")
    config = config_loader.config

    name_loader = NameLoader(config)

    config_file = "config/initialization.json"
    generate_dynasty_definitions(config_file)
    generate_dynasty_name_localization(config_file)
    generate_dynasty_motto_localization(config_file)

    for i in range(NUM_SIMULATIONS):
        if NUM_SIMULATIONS > 1:
            logging.info(f"── Simulation {i + 1} / {NUM_SIMULATIONS} ──")
        simulation = Simulation(config, name_loader)
        simulation.run()


if __name__ == "__main__":
    run_main()