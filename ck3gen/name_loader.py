import os
import random
import logging


class NameLoader:
    def __init__(self, name_list_folder='name_lists'):
        self.name_list_folder = name_list_folder
        # Single shared cache keyed as "culture_gender" strings.
        self.name_cache: dict[str, list[str]] = {}
        if not os.path.isdir(self.name_list_folder):
            logging.warning(f"Name lists folder '{self.name_list_folder}' not found. Using fallback names.")
            os.makedirs(self.name_list_folder, exist_ok=True)

    def _load(self, culture: str, gender: str) -> list[str]:
        """Load and cache the name list for (culture, gender); return the cached list."""
        key = f"{culture}_{gender}"
        if key not in self.name_cache:
            file_path = os.path.join(self.name_list_folder, f"{key}.txt")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    names = [line.strip() for line in f if line.strip()]
                if not names:
                    raise ValueError("Name list is empty.")
                self.name_cache[key] = names
            except (FileNotFoundError, ValueError):
                logging.warning(
                    f"Name file missing or empty for {key}. Using fallback namelist."
                )
                self.name_cache[key] = ["FallbackName1", "FallbackName2"]
        return self.name_cache[key]

    def load_names(self, culture: str, gender: str) -> str:
        """Return a random name for the given culture and gender."""
        return random.choice(self._load(culture, gender))

    def get_all_names(self, culture: str, sex: str) -> list[str]:
        """Return the full name list for the given culture and sex."""
        return self._load(culture, sex)