"""
ck3gen/config_loader.py
~~~~~~~~~~~~~~~~~~~~~~~
Loads, validates, and provides access to the three JSON configuration files:
  - config/initialization.json
  - config/skills_and_traits.json
  - config/life_stages.json

NUM_SIMULATIONS is read from the ``CK3GEN_NUM_SIMULATIONS`` environment
variable (default 1), so it can be overridden without touching source code.
All other formerly hardcoded debug flags have been removed — use the standard
``logging`` level instead (e.g. ``--log-level DEBUG`` or set
``logging.basicConfig(level=logging.DEBUG)`` in your entry point).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Runtime-configurable settings
# ---------------------------------------------------------------------------

# Number of back-to-back simulations to run in a single session.
# Override via environment variable: CK3GEN_NUM_SIMULATIONS=5
NUM_SIMULATIONS: int = int(os.environ.get("CK3GEN_NUM_SIMULATIONS", "1"))


# ---------------------------------------------------------------------------
#  ConfigLoader
# ---------------------------------------------------------------------------


class ConfigLoader:
    """Loads all configuration files and validates their contents."""

    def __init__(self, config_folder: str | Path = "config") -> None:
        self.config_folder = Path(config_folder)
        self.config: dict = {}
        self.dynasty_language_rules: dict[str, list[tuple[str, int, int]]] = {}

        self._load_configs()
        self._validate_configs()
        self._build_language_rules()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load_configs(self) -> None:
        """Read all three JSON config files into ``self.config``."""
        config_files: dict[str, str] = {
            "initialization":  "initialization.json",
            "skills_and_traits": "skills_and_traits.json",
            "life_stages":     "life_stages.json",
        }

        for category, filename in config_files.items():
            path = self.config_folder / filename
            if not path.exists():
                raise FileNotFoundError(
                    f"Configuration file '{filename}' not found in '{self.config_folder}'."
                )
            try:
                self.config[category] = json.loads(path.read_text(encoding="utf-8"))
                logger.debug("Loaded configuration from %s.", filename)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Error parsing '{filename}': {exc}") from exc

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate_configs(self) -> None:
        """Validate all loaded config sections, raising ``ValueError`` on failure."""
        self._validate_initialization()
        self._validate_life_stages()
        self._validate_skills_and_traits()
        self._warn_unused_parameters()

    def _validate_initialization(self) -> None:
        init = self.config.get("initialization", {})

        for key in ("dynasties", "initialCharID", "minYear", "maxYear", "generationMax"):
            if key not in init:
                raise ValueError(f"Missing '{key}' in initialization configuration.")

        dynasties = init.get("dynasties", [])
        if not dynasties:
            raise ValueError("No dynasties defined in initialization configuration.")

        for dynasty in dynasties:
            for field in (
                "dynastyID", "faithID", "cultureID", "gender_law",
                "succession", "progenitorMaleBirthYear", "nameInheritance",
            ):
                if field not in dynasty:
                    raise ValueError(
                        f"Missing '{field}' in dynasty '{dynasty.get('dynastyID', '?')}'."
                    )

            ni = dynasty["nameInheritance"]
            for field in (
                "grandparentNameInheritanceChance",
                "parentNameInheritanceChance",
                "noNameInheritanceChance",
            ):
                if field not in ni:
                    raise ValueError(
                        f"Missing '{field}' in nameInheritance for dynasty '{dynasty['dynastyID']}'."
                    )

            total = sum(ni.values())
            if abs(total - 1.0) >= 1e-6:
                raise ValueError(
                    f"Name inheritance chances for dynasty '{dynasty['dynastyID']}' "
                    f"do not sum to 1.0 (got {total:.6f})."
                )

    def _validate_life_stages(self) -> None:
        life = self.config.get("life_stages", {})

        # Bastardy chances
        for key in ("bastardyChanceMale", "bastardyChanceFemale"):
            if key not in life:
                raise ValueError(f"Missing '{key}' in life_stages configuration.")
            if not (0.0 <= life[key] <= 1.0):
                raise ValueError(f"'{key}' must be between 0.0 and 1.0.")

        # Rate arrays — each must have exactly 121 entries (ages 0–120)
        for rate_key in ("mortalityRates", "marriageRates", "fertilityRates"):
            rates = life.get(rate_key, {})
            for sex in ("Male", "Female"):
                if sex not in rates:
                    raise ValueError(
                        f"{sex} rates are not defined in life_stages.{rate_key}."
                    )
                if len(rates[sex]) != 121:
                    raise ValueError(
                        f"life_stages.{rate_key}.{sex} must have exactly 121 entries "
                        f"(ages 0–120); got {len(rates[sex])}."
                    )

        for key in ("maximumNumberOfChildren", "minimumYearsBetweenChildren"):
            if key not in life:
                raise ValueError(f"Missing '{key}' in life_stages configuration.")
            if not isinstance(life[key], int) or life[key] < 0:
                raise ValueError(f"'{key}' must be a non-negative integer.")

        for key in ("childbirthMinAge", "childbirthMaxAge"):
            if key in life:
                logger.warning(
                    "life_stages parameter '%s' is obsolete and ignored. "
                    "Remove it from your config.",
                    key,
                )

    def _validate_skills_and_traits(self) -> None:
        skills = self.config.get("skills_and_traits", {})

        for key in (
            "sexualityDistribution", "skillProbabilities",
            "educationProbabilities", "personalityTraits",
        ):
            if key not in skills:
                raise ValueError(f"Missing '{key}' in skills_and_traits configuration.")

        exponent = skills.get("educationWeightExponent", 1)
        if not isinstance(exponent, (int, float)) or exponent < 1:
            logger.warning(
                "Invalid 'educationWeightExponent' (%r); defaulting to 1.", exponent
            )
            self.config["skills_and_traits"]["educationWeightExponent"] = 1

    def _warn_unused_parameters(self) -> None:
        """Log a warning for any parameters that are present but no longer used."""
        init    = self.config.get("initialization", {})
        skills  = self.config.get("skills_and_traits", {})
        life    = self.config.get("life_stages", {})

        unused: list[tuple[dict, list[str]]] = [
            (init,   ["bookmarkStartDate", "childrenMax"]),
            (skills, ["inheritanceChance", "downgradeChance", "randomMutationChance", "mutationProbabilities"]),
            (life,   ["battleDeathChance", "illDeathChance", "intrigueDeathChance",
                      "oldDeathMinAge", "oldDeathMaxAge", "siblingMinSpacing"]),
        ]

        for section, keys in unused:
            for key in keys:
                if key in section:
                    logger.warning("Config parameter '%s' is unused and can be removed.", key)

    # ── Language rules ────────────────────────────────────────────────────────

    def _build_language_rules(self) -> None:
        """
        Parse the optional ``languages`` array for every dynasty.

        Each entry must be a comma-separated string: ``"language_id,start_year,end_year"``.
        Malformed entries are skipped with a warning.
        """
        dynasties = self.config.get("initialization", {}).get("dynasties", [])

        for entry in dynasties:
            dynasty_id = entry["dynastyID"]
            rules: list[tuple[str, int, int]] = []

            for spec in entry.get("languages", []):
                parts = spec.split(",")
                if len(parts) != 3:
                    logger.warning(
                        "Bad language spec '%s' in dynasty '%s': "
                        "expected 'language_id,start_year,end_year'.",
                        spec, dynasty_id,
                    )
                    continue
                lang, start, end = parts
                try:
                    rules.append((lang.strip(), int(start), int(end)))
                except ValueError:
                    logger.warning(
                        "Non-integer year in language spec '%s' for dynasty '%s'.",
                        spec, dynasty_id,
                    )

            self.dynasty_language_rules[dynasty_id] = rules

    # ── Public accessors ──────────────────────────────────────────────────────

    def get_initialization_config(self) -> dict:
        return self.config.get("initialization", {})

    def get_dynasty_config(self, dynasty_id: str) -> dict | None:
        dynasties = self.config.get("initialization", {}).get("dynasties", [])
        return next((d for d in dynasties if d["dynastyID"] == dynasty_id), None)

    def get_skills_and_traits_config(self) -> dict:
        return self.config.get("skills_and_traits", {})

    def get_life_stages_config(self) -> dict:
        return self.config.get("life_stages", {})

    def get(self, category: str, key: str, default=None):
        return self.config.get(category, {}).get(key, default)

    def get_language_rules(self) -> dict[str, list[tuple[str, int, int]]]:
        return self.dynasty_language_rules