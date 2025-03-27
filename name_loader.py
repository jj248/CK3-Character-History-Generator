import os
import random
import logging

class NameLoader:
    def __init__(self, name_list_folder='name_lists'):
        self.name_list_folder = name_list_folder
        self.name_cache = {}
        if not os.path.isdir(self.name_list_folder):
            logging.warning(f"Name lists folder '{self.name_list_folder}' not found. Using fallback names.")
            os.makedirs(self.name_list_folder, exist_ok=True)

    def load_names(self, culture, gender):
        """Load names from a file based on culture and gender. If file is not found, return fallback names."""
        key = (culture, gender)
        if key not in self.name_cache:
            file_path = os.path.join(self.name_list_folder, f"{culture}_{gender}.txt")
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    names = [line.strip() for line in file if line.strip()]
                if not names:
                    raise ValueError("Name list is empty.")
            except (FileNotFoundError, ValueError) as e:
                logging.warning(f"Name file not found or empty for {culture}_{gender}. Using fallback names.")
                names = ["Alex", "Jordan"]  # Use more meaningful fallback names
            self.name_cache[key] = names
        return random.choice(self.name_cache[key])

    def get_all_names(self, culture, sex):
        key = f"{culture}_{sex}"
        if key not in self.name_cache:
            file_path = os.path.join(self.name_list_folder, f"{culture}_{sex}.txt")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    names = [line.strip() for line in f if line.strip()]
                    self.name_cache[key] = names
                    if not names:
                        logging.warning(f"Name list for {culture}_{sex} is empty. Ensure {file_path} has valid names.")
            except FileNotFoundError:
                logging.error(f"Name list file not found: {file_path}")
                self.name_cache[key] = []
        return self.name_cache[key]
