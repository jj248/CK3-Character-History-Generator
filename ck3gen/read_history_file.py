import os
import re
from collections import defaultdict

class Character:
    def __init__(self, identifier, name, father, mother, dynasty, female, is_bastard,
                 birth_year, birth_month=None, birth_day=None,
                 death_year=None, death_month=None, death_day=None):
        self.id = identifier
        self.name = name
        self.father = father
        self.mother = mother
        self.dynasty = dynasty
        self.female = female
        self.is_bastard = is_bastard
        self.birth_year = birth_year
        self.birth_month = birth_month if birth_month is not None else 1
        self.birth_day = birth_day if birth_day is not None else 1
        self.death_year = death_year
        self.death_month = death_month
        self.death_day = death_day
        self.is_progenitor = self.check_if_progenitor(identifier)

    def check_if_progenitor(self, identifier):
        return bool(re.search(r"(?<!\d)1$", identifier))

    def __repr__(self):
        return f"<Character {self.name} ({self.id})>"

class CharacterLoader:
    def __init__(self):
        self.characters = {}
        self.dynasties = defaultdict(list)

    def extract_value(self, pattern, content, default=""):
        match = re.search(pattern, content)
        return match.group(1) if match else default

    def load_characters(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            data = f.read()

        # Match character blocks (now filtered for 'line' prefix)
        character_blocks = re.findall(
            r"(\w+)\s*=\s*\{([^}]*)\}",  # Capture character block: name = {...} (non-greedy)
            data,
            re.DOTALL
        )

        for identifier, content in character_blocks:
            # Only process blocks where the identifier starts with 'line'
            if not identifier.startswith("line"):
                continue  # Skip blocks that don't represent characters

            # Extract basic character information
            name = self.extract_value(r"name\s*=\s*(\w+)", content)
            father = self.extract_value(r"father\s*=\s*(\w+)", content, default=None)
            mother = self.extract_value(r"mother\s*=\s*(\w+)", content, default=None)
            dynasty = self.extract_value(r"dynasty\s*=\s*(\w+)", content, default="Lowborn")
            female = bool(re.search(r"female\s*=\s*yes", content))
            is_bastard = bool(re.search(r"trait\s*=\s*bastard", content))

            # Match birth date (relaxed pattern)
            birth_match = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", content)
            
            # Match death event (relaxed pattern)
            death_match = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", content)

            birth_year = birth_month = birth_day = None
            death_year = death_month = death_day = None

            # Debugging prints
            # if birth_match:
            #     print(f"Birth Match Found: {birth_match.group(1)}-{birth_match.group(2)}-{birth_match.group(3)} | {identifier}")
            # else:
            #     print("No Birth Match")
            
            # if death_match:
            #     print(f"Death Match Found: {death_match.group(1)}-{death_match.group(2)}-{death_match.group(3)} | {identifier}")
            # else:
            #     print("No Death Match")

            # If death event is found, extract the date
            if death_match:
                death_year = int(death_match.group(1))
                death_month = int(death_match.group(2))
                death_day = int(death_match.group(3))

            # If birth date is found, extract it
            if birth_match:
                birth_year = int(birth_match.group(1))
                birth_month = int(birth_match.group(2))
                birth_day = int(birth_match.group(3))

            # Create character object
            character = Character(
                identifier, name, father, mother, dynasty, female, is_bastard,
                birth_year, birth_month, birth_day,
                death_year, death_month, death_day
            )

            # Add character to the dictionary of characters and dynasties
            self.characters[identifier] = character
            self.dynasties[dynasty].append(character)

    def get_characters_by_dynasty(self, filename):
        self.load_characters(filename)
        return self.dynasties

def parse_title_history(file_path):
    title_histories = defaultdict(list)

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_title = None
    line_idx = 0

    while line_idx < len(lines):
        line = lines[line_idx].strip()

        # Detect new title block
        title_match = re.match(r'^(\w+)\s*=\s*\{$', line)
        if title_match:
            current_title = title_match.group(1)
            line_idx += 1
            continue

        # Match date block
        date_match = re.match(r'^(\d{1,4}\.\d{1,2}\.\d{1,2})\s*=\s*\{$', line)
        if date_match and current_title:
            current_date = date_match.group(1)
            holder_id = None
            line_idx += 1

            # Read block contents
            while line_idx < len(lines) and not lines[line_idx].strip().startswith('}'):
                inner_line = lines[line_idx].strip()

                # Match holder and ignore comments after '#'
                holder_match = re.match(r'^holder\s*=\s*(\w+)', inner_line)
                if holder_match:
                    holder_id = holder_match.group(1)
                
                line_idx += 1

            # Save only if holder was found
            if holder_id is not None:
                title_histories[current_title].append({
                    "date": current_date,
                    "holder_id": holder_id
                })

        line_idx += 1

    return title_histories

def correlate_characters_and_titles(characters_by_dynasty, title_histories):
    all_characters = {}
    for dynasty_characters in characters_by_dynasty.values():
        for char in dynasty_characters:
            all_characters[char.id] = char  # Flatten all characters for fast lookup

    for title, history in title_histories.items():
        print(f"\n--------\nTitle: {title}\n--------")
        ruler_order = 1

        for entry in history:
            holder_id = entry["holder_id"]

            if holder_id in all_characters:
                character = all_characters[holder_id]
                birth_info = f"{character.birth_year}-{character.birth_month:02d}-{character.birth_day:02d}" if character.birth_year else "Unknown"
                death_info = f"{character.death_year}-{character.death_month:02d}-{character.death_day:02d}" if character.death_year else "Unknown"

                print(f"  Ruler {ruler_order}: {character.name} ({character.id})")
                print(f"    Born: {birth_info}, Died: {death_info}")
                ruler_order += 1
            else:
                print(f"  Ruler {ruler_order}: Unknown character ID '{holder_id}' (Not found)")
                ruler_order += 1




# Example usage
if __name__ == "__main__":
    loader = CharacterLoader()
    history_file = r"C:\GitHub\RealmsInExile\LotRRealmsInExileDev\history\characters\dunedain_arnorian_characters.txt"
    title_histories = parse_title_history(r"C:\GitHub\RealmsInExile\LotRRealmsInExileDev\history\titles\00_e_arnor.txt")
    
    # Debugging check: Does the file exist?
    if not os.path.exists(history_file):
        print(f"❌ ERROR: File not found at: {history_file}")
    else:
        characters_by_dynasty = loader.get_characters_by_dynasty(history_file)
        correlate_characters_and_titles(characters_by_dynasty, title_histories)