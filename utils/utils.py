import random
from datetime import datetime

def generate_random_date(year):
    """Generate a random date with a random month and day, formatted as YYYY.MM.DD."""
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # To avoid invalid dates
    return f"{year}.{month:02}.{day:02}"

def generate_char_id(dynasty_prefix, dynasty_char_counters):
    """Generate a unique character ID using the dynasty prefix."""
    if dynasty_prefix not in dynasty_char_counters:
        dynasty_char_counters[dynasty_prefix] = 1
    else:
        dynasty_char_counters[dynasty_prefix] += 1
    return f"lineof{dynasty_prefix}{dynasty_char_counters[dynasty_prefix]}"
