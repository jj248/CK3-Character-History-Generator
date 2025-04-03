import json
import re
import logging
from collections import defaultdict

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

    def filter_children_by_gender(self, children, female=True):
        """Filter children by gender.
        
        Args:
            children (list): A list of Character objects.
            female (bool): If True, return female children; if False, return male children.

        Returns:
            list: A list of children matching the specified gender.
        """
        return [child for child in children if child.female == female]

    def get_firstborn_son(self, father_id):
        """Find and return the firstborn son of a given character."""
        children = self.get_children_in_birth_order(father_id)
        sons = self.filter_children_by_gender(children, female=False)
        return sons[0] if sons else None  # Return the firstborn son if available

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
    
    def find_successor(self, ruler_id, succession_law="agnatic_primogeniture"):
        """
        Entry point for finding the next heir.
        """
        visited = set()
        return self.find_next_heir(ruler_id, visited, succession_law)

    def find_next_heir(self, person_id, visited, succession_law):
        """
        Recursively determines the next heir by checking descendants, siblings, and then moving up the family tree.
        """
        if person_id in visited:
            return None  # Prevent infinite loops
        visited.add(person_id)

        person = self.characters.get(person_id)
        if not person:
            return None  # If person does not exist

        # Step 1: Look for an heir among direct descendants
        heir = self.find_in_descendants(person_id, succession_law)
        if heir:
            return heir

        # Step 2: If no heir in descendants, check siblings (excluding self)
        if person.father:
            siblings = self.get_children_in_birth_order(person.father)
            siblings = [s for s in siblings if s.id != person_id]  # Exclude self
            for sibling in siblings:
                if self.is_eligible_heir(sibling, succession_law, person.death_year):
                    return sibling
                heir = self.find_next_heir(sibling.id, visited, succession_law)
                if heir:
                    return heir

        # Step 3: If no siblings qualify, check the parent's next heir
        if person.father:
            return self.find_next_heir(person.father, visited, succession_law)
        if person.mother:
            return self.find_next_heir(person.mother, visited, succession_law)

        return None  # No valid heir found

    def find_in_descendants(self, parent_id, succession_law):
        """
        Finds the next heir among a person's direct descendants based on succession laws.
        """
        children = self.get_children_in_birth_order(parent_id)
        males = [c for c in children if not c.female]
        females = [c for c in children if c.female]

        # Define succession rules
        if succession_law == "agnatic_primogeniture":
            eligible_list = males  # Males only
        elif succession_law == "cognatic_primogeniture":
            eligible_list = males + females  # Males first, then females
        elif succession_law == "absolute_primogeniture":
            eligible_list = children  # Birth order only, regardless of gender
        else:
            return None  # Unknown succession law

        # Iterate through eligible heirs
        for candidate in eligible_list:
            if self.is_eligible_heir(candidate, succession_law, candidate.death_year):
                return candidate

            # Check if candidate's descendants can inherit
            heir = self.find_in_descendants(candidate.id, succession_law)
            if heir:
                return heir

        return None  # No suitable heir found

    def is_eligible_heir(self, character, succession_law, date_of_death):
        """
        Checks if a character is a valid heir based on survival and succession laws.
        """
        if not character:
            return False
        if character.is_bastard:
            return False  # Bastards cannot inherit
        if not self.is_alive(character) or character.death_year and character.death_year <= date_of_death:
            return False  # Must be alive at ruler's death
        return True

    def print_family_info(self):
        """Print the family details (ID, father, mother, dynasty, and title inheritance order) of each character, including the progenitor per dynasty."""
        # Find the progenitor for each dynasty
        dynasties_seen = set()

        print("\n")
        # Print family info for each character, excluding those without a dynasty
        for character in self.characters.values():
            if character.dynasty and character.dynasty != "Lowborn":  # Only print characters with a valid dynasty
                dynasty_info = character.dynasty
                # Find the character's title order within their dynasty
                title_order = None
                sorted_chars = self.get_children_in_birth_order(character.dynasty)
                for idx, char in enumerate(sorted_chars):
                    if char.id == character.id:
                        title_order = idx + 1  # Title order is the index + 1
                        break

                father_info = character.father if character.father else "No father"
                mother_info = character.mother if character.mother else "No mother"
                print(f"Character ID: {character.id}, Father ID: {father_info}, Mother ID: {mother_info}, Dynasty: {dynasty_info}, Ruler: {title_order}, Alive: {self.is_alive(character)}, Progenitor: {character.is_progenitor}")

        
        # Print family info for each character, excluding those without a dynasty
        for character in self.characters.values():
            if character.dynasty and character.dynasty != "Lowborn":  # Only print characters with a valid dynasty
                dynasty_info = character.dynasty
                # Find the character's title order within their dynasty
                title_order = None
                sorted_chars = sorted(self.dynasties[character.dynasty], key=lambda x: (x.birth_year, x.birth_month or 1, x.birth_day or 1))
                for idx, char in enumerate(sorted_chars):
                    if char.id == character.id:
                        title_order = idx + 1  # Title order is the index + 1
                        break

                father_info = character.father if character.father else "No father"
                mother_info = character.mother if character.mother else "No mother"
                print(f"Character ID: {character.id}, Father ID: {father_info}, Mother ID: {mother_info}, Dynasty: {dynasty_info}, Ruler: {title_order}, Alive: {self.is_alive(character)}")

class TitleHistory:
    def __init__(self, character_loader, config_file):
        self.titles = {}  # This will store dynasty and ruler info
        self.death_dates = {}  # This will track the death dates of rulers
        self.characters = character_loader.characters  # Use characters loaded in memory
        self.dynasties = character_loader.dynasties  # Access the dynasties dictionary
        self.config = self.load_json_file(config_file)

    def load_json_file(self, filename):
        try:
            with open(filename, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data.get("dynasties", [])  # Extracts the list under "dynasties"
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading file '{filename}': {e}")
            return []

    def primogeniture_inheritance(self, characters, gender_law="male", current_date=None):
        if current_date is None:
            current_date = (9999, 12, 31)  # Default to a far future date if no date is provided
        else:
            current_date = (current_date, 12, 31)  # Ensure current_date is in tuple format (year, month, day)

        # Filter based on gender law
        if gender_law == "male":
            eligible = [c for c in characters if not c.female]  # Only male characters
        elif gender_law == "female":
            eligible = [c for c in characters if c.female]  # Only female characters
        elif gender_law == "equal":
            eligible = characters  # All characters are eligible, regardless of gender
        else:
            logging.error(f"Invalid gender law: {gender_law}. Valid options are 'male', 'female', or 'equal'.")
            return []

        # Helper function to get the full death date as a tuple (year, month, day)
        def get_death_date(character):
            if character.death_year is None:
                return None  # Alive characters
            # If no month or day, use the latest possible day for that year
            month = character.death_month if character.death_month is not None else 12
            day = character.death_day if character.death_day is not None else 31
            return (character.death_year, month, day)

        # Filter out dead characters (those whose death date is before the current date)
        alive_eligible = [
            c for c in eligible
            if (get_death_date(c) is None or get_death_date(c) >= current_date)  # Still alive
            and (c.birth_year, c.birth_month or 1, c.birth_day or 1) <= current_date  # Already born
        ]

        # Sort characters first by birth date (year, month, day)
        sorted_alive_eligible = sorted(alive_eligible, key=lambda c: (c.birth_year, c.birth_month or 1, c.birth_day or 1))
        
        # Now pick the first eligible character (the one with the earliest birth date)
        for character in sorted_alive_eligible:
            # Check if the character is alive during the current_date
            if (character.birth_year, character.birth_month or 1, character.birth_day or 1) <= current_date:
                # logging.info(f"Selected ruler: {character.name} (ID: {character.id}) for year {current_date[0]}")
                return character  # Return the first character who is eligible and alive during the transition

        return None  # No eligible characters

    def assign_titles(self):
        dynasty_map = defaultdict(list)

        # Organize characters by dynasty
        for char_id, char_data in self.characters.items():
            dynasty_map[char_data.dynasty].append(char_data)

        for dynasty_id, characters in dynasty_map.items():
            dynasty_config = next((d for d in self.config if d["dynastyID"] == dynasty_id), None)
            if not dynasty_config:
                continue

            inheritance_law = dynasty_config.get("inheritanceLaw", "primogeniture")
            gender_law = dynasty_config.get("genderLaw", "male")

            # logging.info(f"Processing dynasty {dynasty_id} with inheritance law: {inheritance_law} and gender law: {gender_law}")

            # Sort characters by birth year
            sorted_chars = sorted(characters, key=lambda x: x.birth_year or 9999)

            # Determine the starting year: the birth year of the first character in the dynasty
            start_year = sorted_chars[0].birth_year

            # Initialize the current year to the starting year of the dynasty
            current_year = start_year

            previous_ruler_id = None  # Track the previous ruler
            previous_ruler_death_date = None  # Track the previous ruler's death date

            while current_year <= 9999:  # Adjust this as needed for the duration you want to track
                # Get the eligible ruler for the current year based on primogeniture and gender laws
                ruler = self.primogeniture_inheritance(sorted_chars, gender_law, current_year)
                if ruler:
                    # For the first ruler, assign reign starting at birth year + 18
                    if previous_ruler_id is None:
                        current_year = ruler.birth_year + 18  # Use birth year + 18 for the first ruler
                    else:
                        # Use previous ruler's death date for the transition
                        previous_ruler = self.characters.get(previous_ruler_id)
                        if previous_ruler and previous_ruler.death_year is not None:
                            current_year = previous_ruler.death_year

                    # Apply inheritance and set the title
                    self.titles[dynasty_id] = ruler.id
                    self.death_dates[dynasty_id] = previous_ruler_death_date  # Track the previous ruler's death date
                    # logging.info(f"Assigned title for dynasty {dynasty_id} to {ruler.name} in year {current_year}")
                    previous_ruler_id = ruler.id  # Set this ruler as the previous ruler

                    # Track the ruler's death date and update the current year for the next ruler
                    if ruler.death_year is not None:
                        previous_ruler_death_date = f"{ruler.death_year}.{ruler.death_month:02d}.{ruler.death_day:02d}"
                        current_year = ruler.death_year + 1  # Move to the year after the ruler dies
                    else:
                        # If the ruler has no death year, break the loop
                        break  # Exit the loop as the ruler is still alive

                else:
                    break  # Exit if no ruler was found

    def export_title_history(self, filename="title_history.txt"):
        with open(filename, "w", encoding="utf-8") as file:
            for dynasty, holder in self.titles.items():
                # Start by writing the placeholder title for the dynasty
                file.write(f"placeholder_title = {{\n")

                previous_ruler_death_year = None  # Start with no previous ruler
                previous_ruler_death_month = None  # Start with no previous ruler
                previous_ruler_death_day = None  # Start with no previous ruler
                current_year = None  # This will track the current year for assigning rulers

                # First, we need to sort characters by birth year so we can process them in the right order
                sorted_chars = sorted(
                    self.dynasties[dynasty], 
                    key=lambda x: (x.death_year or 9999, x.death_month or 12, x.death_day or 31)
                )

                # Find the character with the "dynasty_id1" id
                dynasty_id1_character = None
                for char in sorted_chars:
                    # print(char)
                    if char.id == f"{dynasty}_1":  # assuming `dynasty_id1` refers to something like 'dynasty_1'
                        dynasty_id1_character = char
                        break

                if dynasty_id1_character:
                    # Filter out any character before the "dynasty_id1" character
                    start_index = sorted_chars.index(dynasty_id1_character)
                    sorted_chars = sorted_chars[start_index:]

                for char in sorted_chars:
                    # For the first ruler, assign them at age 18 (birth year + 18)
                    if current_year is None:
                        current_year = char.birth_year + 18  # The first ruler comes into power at age 18
                        file.write(f"    {current_year}.01.01 = {{\n")
                        file.write(f"        holder = {char.id} #{char.name}\n")
                        file.write(f"    }}\n")
                    else:
                        # For subsequent rulers, use the previous ruler's death year
                        death = f"{char.death_year}.{char.death_month:02d}.{char.death_day:02d}" if char.death_year else None

                        if previous_ruler_death_year:
                            # The next ruler starts the year after the previous ruler dies
                            current_year = previous_ruler_death_year
                            death = f"{previous_ruler_death_year}.{previous_ruler_death_month:02d}.{previous_ruler_death_day:02d}"

                        if death:
                            file.write(f"    {death} = {{\n")
                            file.write(f"        holder = {char.id} #{char.name}\n")
                            file.write(f"    }}\n")

                    # Update the previous ruler's death date to be the current ruler's death date
                    if char.death_year is not None:
                        previous_ruler_death_year = char.death_year
                        previous_ruler_death_month = char.death_month
                        previous_ruler_death_day = char.death_day

                file.write(f"}}\n")

        logging.info(f"Title history exported to {filename}.")
