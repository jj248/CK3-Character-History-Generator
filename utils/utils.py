"""
utils/utils.py
~~~~~~~~~~~~~~
Shared utility helpers used across the CK3 Character History Generator.
"""

from __future__ import annotations

import random


def generate_random_date(year: int) -> str:
    """Return a random date string in YYYY.MM.DD format for the given year."""
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Capped at 28 to avoid invalid calendar dates
    return f"{year}.{month:02}.{day:02}"


def generate_char_id(dynasty_prefix: str, dynasty_char_counters: dict[str, int]) -> str:
    """Generate a unique character ID using the dynasty prefix.

    Increments the per-dynasty counter on every call and returns an ID of
    the form ``lineof<prefix><n>``.
    """
    dynasty_char_counters[dynasty_prefix] = dynasty_char_counters.get(dynasty_prefix, 0) + 1
    return f"lineof{dynasty_prefix}{dynasty_char_counters[dynasty_prefix]}"