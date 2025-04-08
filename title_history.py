import json
import re
import logging
from collections import defaultdict
from datetime import datetime

# Set up logging to display info and errors
logging.basicConfig(level=logging.INFO)

class Character:
    def __init__(self, identifier, name, father, mother, dynasty, female, is_bastard, birth_year, birth_month=None, birth_day=None, death_year=None, death_month=None, death_day=None):
        self.id = identifier
        self.name = name
        self.father = father
        self.mother = mother
        self.dynasty = dynasty
        self.female = female
        self.is_bastard = is_bastard
        self.birth_year = birth_year
        self.birth_month = birth_month if birth_month is not None else 1  # Default to January
        self.birth_day = birth_day if birth_day is not None else 1  # Default to the 1st
        self.death_year = death_year
        self.death_month = death_month
        self.death_day = death_day
        self.is_progenitor = self.check_if_progenitor(identifier)

    def check_if_progenitor(self, identifier):
        """Determine if the character is the progenitor based on their ID pattern."""
        return bool(re.search(r"(?<!\d)1$", identifier))  # Ensures '1' is the only trailing digit

    def __repr__(self):
        return f"<Character {self.name} ({self.id})>"

class CharacterLoader:
    def __init__(self):
        self.characters = {}
        self.dynasties = defaultdict(list)

    def get_children_in_birth_order(self, parent_id):
        """Return a list of a person's children, sorted by birth date."""
        children = [
            character for character in self.characters.values()
            if character.father == parent_id or character.mother == parent_id
        ]

        # Sort by birth date: Year, then Month, then Day
        return sorted(children, key=lambda c: (c.birth_year, c.birth_month or 1, c.birth_day or 1))

    def load_characters(self, filename):
        """Parse the .txt file to extract character details and store them in memory."""
        with open(filename, "r", encoding="utf-8") as f:
            data = f.read()

        character_blocks = re.findall(r"(\w+) = \{\s*((?:[^{}]*|\{(?:[^{}]*|\{[^}]*\})*\})*)\s*\}", data, re.DOTALL)

        for identifier, content in character_blocks:
            name = self.extract_value(r"name\s*=\s*(\w+)", content)
            father = self.extract_value(r"father\s*=\s*(\w+)", content, default=None)
            mother = self.extract_value(r"mother\s*=\s*(\w+)", content, default=None)
            dynasty = self.extract_value(r"dynasty\s*=\s*(\w+)", content, default="Lowborn")
            female = bool(re.search(r"female\s*=\s*yes", content))
            is_bastard = bool(re.search(r"trait\s*=\s*bastard", content))

            birth_match = re.search(r"(\d{4})\.(\d{2})\.(\d{2})\s*=\s*\{\s*birth\s*=\s*yes", content)
            death_match = re.search(r"(\d{4})\.(\d{2})\.(\d{2})\s*=\s*\{\s*death", content)

            # Ensure that death_year, death_month, and death_day are properly set
            death_year = int(death_match.group(1)) if death_match else None
            death_month = int(death_match.group(2)) if death_match else None
            death_day = int(death_match.group(3)) if death_match else None

            birth_year = int(birth_match.group(1)) if birth_match else None
            birth_month = int(birth_match.group(2)) if birth_match else None
            birth_day = int(birth_match.group(3)) if birth_match else None



            # Create a Character object and add it to the list
            character = Character(
                identifier, name, father, mother, dynasty, female, is_bastard, birth_year, birth_month, birth_day, death_year, death_month, death_day
            )
            self.characters[identifier] = character
            self.dynasties[dynasty].append(character)

    def extract_value(self, pattern, content, default=""):
        match = re.search(pattern, content)
        return match.group(1) if match else default
    
    def is_alive(self, character):
        """Return True if the character is alive, False if dead."""
        if character.death_year is None:
            return True  # Character is alive if no death year is set
        current_year = 2025  # Adjust based on the current year in your simulation
        return character.death_year > current_year or (character.death_year == current_year and character.death_month >= 1)

    def print_family_info(self):
        """Print the family details (ID, father, mother, dynasty, and title inheritance order) of each character, including the progenitor per dynasty."""
        # Find the progenitor for each dynasty
        dynasties_seen = set()

        print("\n")
        # Print family info for each character, excluding those without a dynasty
        for character in self.characters.values():
            if character.dynasty and character.dynasty != "Lowborn":  # Only print characters with a valid dynasty
                dynasty_info = character.dynasty
                father_info = character.father if character.father else "No father"
                mother_info = character.mother if character.mother else "No mother"
                print(f"Character ID: {character.id}, Father ID: {father_info}, Mother ID: {mother_info}, Dynasty: {dynasty_info}, Progenitor: {character.is_progenitor}")

class TitleHistory:
    def __init__(self, character_loader, config_file):
        self.titles = {}  # dynasty_name: list of (ruler_id, start_year, end_year)
        self.death_dates = {}  # character_id: (year, month, day)
        self.characters = character_loader.characters
        self.dynasties = character_loader.dynasties
        self.config = self.load_json_file(config_file)

    def load_json_file(self, filename):
        try:
            with open(filename, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data.get("dynasties", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading file '{filename}': {e}")
            return []

    def build_title_histories(self):
        """Main method to process all dynasties and build succession timelines."""
        for dynasty in self.dynasties:
            progenitor = self.find_progenitor(dynasty)
            if not progenitor:
                continue

            title_line = []
            current_ruler = progenitor
            rule_start = self.get_birth_date(current_ruler)

            while current_ruler:
                rule_end = self.get_death_date(current_ruler)
                title_line.append((current_ruler.id, *rule_start, *rule_end))
                next_ruler = self.find_successor(current_ruler, rule_end)
                current_ruler = next_ruler
                rule_start = rule_end if next_ruler else None

            self.titles[dynasty] = title_line

    def find_progenitor(self, dynasty):
        """Find the progenitor (ID ending in '1') of a dynasty."""
        for person in self.dynasties[dynasty]:
            if person.is_progenitor:
                return person
        return None

    def find_successor(self, ruler, from_date):
        """Perform DFS starting from ruler to find the next eligible heir."""
        visited = set()
        return self.dfs_search(ruler, from_date, visited)

    def dfs_search(self, person, from_date, visited):
        """Depth-First Search to find next valid heir from this person downward."""
        if person.id in visited:
            return None
        visited.add(person.id)

        # Get children in birth order
        children = self.get_children_in_birth_order(person.id)

        # 1. Male children and descendants
        for child in children:
            if not child.female and self.valid_successor(child, from_date):
                return child
            result = self.dfs_search(child, from_date, visited) if not child.female else None
            if result:
                return result

        # 2. Female children and their descendants
        for child in children:
            if child.female:
                if self.valid_successor(child, from_date):
                    return child
                result = self.dfs_search(child, from_date, visited)
                if result:
                    return result

        # 3. Go up to parent's siblings (uncles/aunts and their lines)
        father = self.characters.get(person.father)
        if father:
            siblings = self.get_children_in_birth_order(father.id)
            for sibling in siblings:
                if sibling.id != person.id:
                    result = self.dfs_search(sibling, from_date, visited)
                    if result:
                        return result

        # 4. Absolute fallback — check all bastards in dynasty
        if person.dynasty in self.dynasties:
            for candidate in self.dynasties[person.dynasty]:
                if candidate.is_bastard and self.valid_successor(candidate, from_date):
                    return candidate

        return None

    def valid_successor(self, candidate, from_date):
        """Return True if the candidate is eligible to inherit after 'from_date'."""
        if candidate.birth_year is None:
            return False

        c_birth = self.get_birth_date(candidate)
        c_death = self.get_death_date(candidate)

        # Must be born before the previous ruler died
        if c_birth > from_date:
            return False

        # Must be alive during or after ruler's death
        now = datetime.now()
        if c_death <= from_date:
            return False

        return True

    def get_birth_date(self, person):
        return (
            person.birth_year or 0,
            person.birth_month or 1,
            person.birth_day or 1
        )

    def get_death_date(self, person):
        # Assume characters without death dates die far in the future
        return (
            person.death_year or 9999,
            person.death_month or 12,
            person.death_day or 31
        )

    def get_children_in_birth_order(self, parent_id):
        """Return children of a given parent in birth order."""
        children = [
            char for char in self.characters.values()
            if char.father == parent_id or char.mother == parent_id
        ]
        return sorted(children, key=lambda c: (c.birth_year, c.birth_month or 1, c.birth_day or 1))

    def convert_to_ingame_date(self, year):
        """Convert the year into T.A. or S.A. format based on cutoff points."""
        if isinstance(year, int) or (isinstance(year, str) and year.isdigit()):
            year = int(year)
            if year > 4033:
                return f"T.A. {year - 4033}"  # Fourth Age
            elif 592 < year <= 4033:
                return f"F.A. {year - 592}"  # Third Age
            else:
                return f"S.A. {year}"  # Second Age fallback
        return "?"

    def print_title_histories(self):
        """Print each dynasty's rulers to the console with in-game formatted dates."""
        for dynasty, rulers in self.titles.items():
            print(f"\n--- Dynasty: {dynasty} ---")
            for ruler_id, by, bm, bd, dy, dm, dd in rulers:
                inherited = f"{self.convert_to_ingame_date(by)} {bm:02}.{bd:02}"
                died = f"{self.convert_to_ingame_date(dy)} {dm:02}.{dd:02}"
                print(f"Ruler: {ruler_id} | Inherited: {inherited} | Died: {died}")

    def write_title_histories_to_file(self):
        """Write the title history to 'title_history.txt'."""
        with open('title_history.txt', 'w', encoding='utf-8') as file:
            for dynasty, rulers in self.titles.items():
                # Write the placeholder_title header
                file.write("placeholder_title = {\n")
                
                placeholder_title = {}
                
                for ruler_id, by, bm, bd, dy, dm, dd in rulers:
                    # Find the ruler’s name
                    ruler_name = self.characters[ruler_id].name if ruler_id in self.characters else "Unknown"
                    dynasty_name = self.characters[ruler_id].dynasty
                    
                    # Add ruler to the dynasty's placeholder_title
                    placeholder_title[f"{by:04}.{bm:02}.{bd:02}"] = {
                        "holder": f"{ruler_id}"
                    }
                    
                    # If there's a next ruler, we need to mark the previous ruler's end date
                    if rulers.index((ruler_id, by, bm, bd, dy, dm, dd)) + 1 < len(rulers):
                        next_ruler = rulers[rulers.index((ruler_id, by, bm, bd, dy, dm, dd)) + 1]
                        next_start_year, next_start_month, next_start_day = next_ruler[1], next_ruler[2], next_ruler[3]
                        placeholder_title[f"{next_start_year:04}.{next_start_month:02}.{next_start_day:02}"] = {
                            "holder": f"{next_ruler[0]} #{self.characters[next_ruler[0]].name}"
                        }

                # Write placeholder_title entries to the file
                for date, entry in placeholder_title.items():
                    file.write(f"    {date} = {{\n")
                    file.write(f"        holder = {entry['holder']}\n")
                    file.write("    }\n")
                
                file.write("}\n")  # Close the placeholder_title block
                file.write("\n")  # Add a blank line between dynasties
