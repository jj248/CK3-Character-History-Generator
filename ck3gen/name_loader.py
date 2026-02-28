"""
ck3gen/name_loader.py
~~~~~~~~~~~~~~~~~~~~~
Loads culture-specific name lists from text files and provides random
name selection with an in-memory cache to avoid repeated disk reads.

Name files must be located in the configured folder and follow the naming
convention ``<culture>_<gender>.txt`` where gender is lowercase
(e.g. ``drenim_male.txt``).
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)


class NameLoader:
    """Loads and caches culture/gender name lists from disk."""

    def __init__(self, name_list_folder: str | Path = "name_lists") -> None:
        self._folder = Path(name_list_folder)
        # Cache keyed by (culture, gender) where gender is always lowercase.
        self._cache: dict[tuple[str, str], list[str]] = {}

        if not self._folder.is_dir():
            logger.warning(
                "Name lists folder '%s' not found. Using fallback names.",
                self._folder,
            )
            self._folder.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    #  Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_key(culture: str, gender: str) -> tuple[str, str]:
        """Normalise a culture/gender pair to a consistent lowercase cache key."""
        return (culture, gender.lower())

    def _load(self, culture: str, gender: str) -> list[str]:
        """Load names from disk into the cache if not already present."""
        key = self._cache_key(culture, gender)
        if key in self._cache:
            return self._cache[key]

        file_path = self._folder / f"{culture}_{gender.lower()}.txt"
        names: list[str] = []

        try:
            names = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not names:
                raise ValueError("Name list is empty.")
        except FileNotFoundError:
            logger.warning("Name file not found: %s. Using fallback names.", file_path)
            names = ["FallbackName1", "FallbackName2"]
        except ValueError:
            logger.warning("Name file is empty: %s. Using fallback names.", file_path)
            names = ["FallbackName1", "FallbackName2"]

        self._cache[key] = names
        return names

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def load_names(self, culture: str, gender: str) -> str:
        """Return a single random name for the given culture and gender."""
        return random.choice(self._load(culture, gender))

    def get_all_names(self, culture: str, gender: str) -> list[str]:
        """Return the full name list for the given culture and gender."""
        names = self._load(culture, gender)
        if not names:
            logger.error(
                "No names available for culture '%s', gender '%s'.",
                culture,
                gender,
            )
        return names