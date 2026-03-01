import json
import os
import re
import logging
from collections import defaultdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

############################
# Enums for Succession/Gender
############################

class SuccessionType(Enum):
    PRIMOGENITURE = "primogeniture"
    ULTIMOGENITURE = "ultimogeniture"
    SENIORITY = "seniority"

class GenderLaw(Enum):
    AGNATIC = "agnatic"
    AGNATIC_COGNATIC = "agnatic_cognatic"
    ABSOLUTE_COGNATIC = "absolute_cognatic"
    ENATIC = "enatic"
    ENATIC_COGNATIC = "enatic_cognatic"

############################
# Character and Loader
############################

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
        self.birth_month = birth_month if birth_month is not None else 1  # Default to January
        self.birth_day = birth_day if birth_day is not None else 1        # Default to the 1st
        self.death_year = death_year
        self.death_month = death_month
        self.death_day = death_day
        self.is_progenitor = self.check_if_progenitor(identifier)

    def check_if_progenitor(self, identifier):
        """Determine if the character is the progenitor based on their ID pattern:
           e.g., an ID ending in '1', with no extra digits trailing."""
        return bool(re.search(r"(?<!\d)1$", identifier))  # Ensures '1' is the only trailing digit

    def __repr__(self):
        return f"<Character {self.name} ({self.id})>"

class CharacterLoader:
    def __init__(self):
        self.characters = {}
        self.dynasties = defaultdict(list)

    def load_characters(self, filename):
        """Parse the .txt file to extract character details and store them in memory."""
        with open(filename, "r", encoding="utf-8") as f:
            data = f.read()

        # This regex might need adjusting if your data has quotes or extra spaces
        character_blocks = re.findall(
            r"(\w+) = \{\s*((?:[^{}]*|\{(?:[^{}]*|\{[^}]*\})*\})*)\s*\}",
            data,
            re.DOTALL
        )

        for identifier, content in character_blocks:
            name = self.extract_value(r"name\s*=\s*(\w+)", content)
            father = self.extract_value(r"father\s*=\s*(\w+)", content, default=None)
            mother = self.extract_value(r"mother\s*=\s*(\w+)", content, default=None)
            dynasty = self.extract_value(r"dynasty\s*=\s*(\w+)", content, default="Lowborn")
            female = bool(re.search(r"female\s*=\s*yes", content))
            is_bastard = bool(re.search(r"trait\s*=\s*bastard", content))

            birth_match = re.search(r"(\d{4})\.(\d{2})\.(\d{2})\s*=\s*\{\s*birth\s*=\s*yes", content)
            death_year = death_month = death_day = None
            for m in re.finditer(r"(\d{4})\.(\d{2})\.(\d{2})\s*=\s*\{([^}]*)\}", content, re.DOTALL):
                y, mo, d, inner = m.group(1), m.group(2), m.group(3), m.group(4)
                if re.search(r"\bdeath\b", inner):
                    death_year  = int(y)
                    death_month = int(mo)
                    death_day   = int(d)
                    break

            birth_year = int(birth_match.group(1)) if birth_match else None
            birth_month = int(birth_match.group(2)) if birth_match else None
            birth_day = int(birth_match.group(3)) if birth_match else None

            # Create a Character object
            character = Character(
                identifier, name, father, mother, dynasty, female, is_bastard,
                birth_year, birth_month, birth_day,
                death_year, death_month, death_day
            )
            self.characters[identifier] = character
            self.dynasties[dynasty].append(character)

    def extract_value(self, pattern, content, default=""):
        match = re.search(pattern, content)
        return match.group(1) if match else default
    
    def is_alive(self, character):
        """
        Return True if the character is 'alive' relative to some 
        current year in your simulation. 
        This is separate from 'posthumous inheritance' logic.
        """
        if character.death_year is None:
            return True  # No death year => considered alive
        current_year = 2025  # or something else
        # If death year > current year => alive, etc.
        return (character.death_year > current_year or
                (character.death_year == current_year and (character.death_month or 12) >= 1))

    def print_family_info(self):
        """Debug method to list each character with father, mother, etc."""
        print("\n--- Family Info ---")
        for character in self.characters.values():
            if character.dynasty and character.dynasty != "Lowborn":
                dynasty_info = character.dynasty
                father_info = character.father if character.father else "No father"
                mother_info = character.mother if character.mother else "No mother"
                print(
                    f"Character ID: {character.id}, "
                    f"Father ID: {father_info}, "
                    f"Mother ID: {mother_info}, "
                    f"Dynasty: {dynasty_info}, "
                    f"Progenitor: {character.is_progenitor}"
                )

############################
# TitleHistory with New Succession Logic
############################

class TitleHistory:
    def __init__(self, character_loader, config_file):
        self.titles = {}   # dynasty_name -> list of (ruler_id, startY, startM, startD, endY, endM, endD)
        self.characters = character_loader.characters
        self.dynasties = character_loader.dynasties 
        self.config = self.load_json_file(config_file)
        self.parent_to_children = defaultdict(list)
        # After all characters are loaded, build an index:
        for char_id, char in self.characters.items():
            if char.father in self.characters:
                self.parent_to_children[char.father].append(char)
            if char.mother in self.characters:
                self.parent_to_children[char.mother].append(char)

    def load_json_file(self, filename):
        """
        Expects a JSON file with a "dynasties" key, containing a list of dynasty configs:
        {
          "dynasties": [
            {
              "name": "HouseDurin",
              "succession": "PRIMOGENITURE",
              "gender_law": "AGNATIC"
            },
            ...
          ]
        }
        """
        try:
            with open(filename, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data.get("dynasties", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Error loading file '{filename}': {e}")
            return []

    ###########################################
    # Public method to build all Title Histories
    ###########################################
    def build_title_histories(self):
        """
        For each dynasty, find the progenitor and build a timeline of rulers
        until we reach someone who is still alive or the line runs out.
        """
        dynasty_settings = self.parse_config()
        
        for dynasty_name, members in self.dynasties.items():
            # 1. Determine laws
            succession_type, gender_law = dynasty_settings.get(
                dynasty_name,
                (SuccessionType.PRIMOGENITURE, GenderLaw.AGNATIC_COGNATIC)
            )

            # 2. Find progenitor
            progenitor = self.find_progenitor(dynasty_name)
            if not progenitor:
                continue

            title_line = []
            current_ruler = progenitor
            rule_start = self.get_birth_date(current_ruler)

            while current_ruler:
                # Get date of death
                rule_end = self.get_death_date(current_ruler)  # e.g. (9999,12,31) if no death date

                # If rule_end indicates "still alive" (your sentinel for no date):
                # We'll say if it exactly equals (9999,12,31), that means they're living or immortal
                if rule_end == (9999, 12, 31):
                    # They are still alive => add them to timeline once, then stop
                    title_line.append((current_ruler.id, *rule_start, *rule_end))
                    break

                # Otherwise, record them and find their successor
                title_line.append((current_ruler.id, *rule_start, *rule_end))
                
                # Move on to the next heir
                next_ruler = self.determine_heir(current_ruler, succession_type, gender_law)
                current_ruler = next_ruler
                rule_start = rule_end if next_ruler else None

            self.titles[dynasty_name] = title_line

    def parse_config(self):
        """
        Create a dictionary:
          {
            dynasty_name: (SuccessionType.X, GenderLaw.Y),
            ...
          }
        from the JSON config data
        """
        results = {}
        for entry in self.config:
            name = entry.get("dynastyID")
            if not name:
                continue
            # Parse succession
            succ = entry.get("succession", "PRIMOGENITURE").upper()
            try:
                succession_type = SuccessionType[succ]
            except KeyError:
                succession_type = SuccessionType.PRIMOGENITURE

            # Parse gender law
            gl = entry.get("gender_law", "AGNATIC_COGNATIC").upper()
            try:
                gender_law = GenderLaw[gl]
            except KeyError:
                gender_law = GenderLaw.AGNATIC_COGNATIC

            results[name] = (succession_type, gender_law)
        return results

    def find_progenitor(self, dynasty):
        """Return the character in self.dynasties[dynasty] whose is_progenitor == True"""
        for person in self.dynasties[dynasty]:
            if person.is_progenitor:
                return person
        return None

    ###########################################
    # Determining Heirs
    ###########################################

    def determine_heir(self, ruler, succession_type, gender_law):
        """
        Main entry point: pick the next ruler after 'ruler' dies,
        based on the specified succession type and gender law.
        Returns a Character or None if no valid heir.
        """
        # We'll compute the parent's date of death so we know who was "alive" or "born" at that time
        parent_death_date = self.get_death_date(ruler)  # (year, month, day)

        if succession_type == SuccessionType.SENIORITY:
            return self.find_heir_seniority(ruler, gender_law, parent_death_date)

        # For Primogeniture / Ultimogeniture, do a 2-stage search:
        # 1) legitimate only
        visited = set()
        heir = self.find_heir_primoultimo(ruler, succession_type, gender_law, parent_death_date, visited, allow_bastards=False)
        if heir:
            return heir
        # 2) fallback with bastards
        visited_bastards = set()
        return self.find_heir_primoultimo(ruler, succession_type, gender_law, parent_death_date, visited_bastards, allow_bastards=True)

    def find_heir_seniority(self, ruler, gender_law, parent_death_date):
        """
        Seniority: pick the single oldest living valid member of the entire dynasty 
        who was alive/eligible at parent's death date. If none, fallback to bastards.
        """
        dynasty_members = self.dynasties.get(ruler.dynasty, [])
        # 1. Try legitimate
        heir = self.pick_oldest_living_valid(dynasty_members, gender_law, parent_death_date, allow_bastards=False)
        if heir:
            return heir
        # 2. Fallback to bastards
        return self.pick_oldest_living_valid(dynasty_members, gender_law, parent_death_date, allow_bastards=True)

    def pick_oldest_living_valid(self, members, gender_law, parent_death_date, allow_bastards):
        """
        Return the single oldest living member (by birth date ascending) 
        who is valid under the chosen gender law, was born before parent's death date,
        and is either not a bastard or we allow bastards.
        """
        valid = []
        for c in members:
            if not allow_bastards and c.is_bastard:
                continue
            if not self.is_valid_by_gender_law(c, gender_law):
                continue
            if not self.was_alive_or_posthumous(c, parent_death_date):
                continue
            valid.append(c)

        # Sort by birth date ascending => oldest first
        valid.sort(key=lambda x: self.get_birth_date(x))
        # Return the first truly "alive" at parent's death date 
        # or at least not disqualified by it.
        for candidate in valid:
            # If candidate died before parent_death_date, that means there's no living line 
            # for them unless we do posthumous. But seniority doesn't do "posthumous inheritance" 
            # in the same sense. If you want to allow dead to pass it on in seniority, you'd 
            # need a big genealogical check. Typically seniority is just "who's oldest and still living?"
            if self.is_alive_at(candidate, parent_death_date):
                return candidate
        return None

    def find_heir_primoultimo(self, ruler, succession_type, gender_law, parent_death_date, visited, allow_bastards):
        if ruler is None:
            return None
        if ruler.id in visited:
            return None
        visited.add(ruler.id)

        # 1. Gather children (already unsorted).
        children = self.get_children_in_birth_order(ruler.id)

        # 2. Filter out ineligible
        valid_kids = []
        for child in children:
            if child.is_bastard and not allow_bastards:
                continue
            if not self.is_valid_by_gender_law(child, gender_law):
                continue
            # Must be born on/before parent's death date
            if self.get_birth_date(child) > parent_death_date:
                continue
            valid_kids.append(child)

        # 3. Sort them by your law:
        # - For AGNATIC/ENATIC, is_valid_by_gender_law already excludes the opposite gender.
        # - For AGNATIC_COGNATIC or ENATIC_COGNATIC, we do a male-first or female-first partition.

        reverse_sort = (succession_type == SuccessionType.ULTIMOGENITURE)

        if gender_law == GenderLaw.AGNATIC_COGNATIC:
            # partition
            male_kids = [c for c in valid_kids if not c.female]
            female_kids = [c for c in valid_kids if c.female]
            male_kids.sort(key=lambda c: self.get_birth_date(c), reverse=reverse_sort)
            female_kids.sort(key=lambda c: self.get_birth_date(c), reverse=reverse_sort)
            ordered_kids = male_kids + female_kids

        elif gender_law == GenderLaw.ENATIC_COGNATIC:
            # partition reversed
            female_kids = [c for c in valid_kids if c.female]
            male_kids = [c for c in valid_kids if not c.female]
            female_kids.sort(key=lambda c: self.get_birth_date(c), reverse=reverse_sort)
            male_kids.sort(key=lambda c: self.get_birth_date(c), reverse=reverse_sort)
            ordered_kids = female_kids + male_kids

        else:
            # all other laws => single sorted list
            ordered_kids = sorted(valid_kids, key=lambda c: self.get_birth_date(c), reverse=reverse_sort)

        # 4. Check each child in that new order
        for child in ordered_kids:
            if self.is_alive_at(child, parent_death_date):
                return child
            else:
                # posthumous pass
                next_heir = self.find_heir_primoultimo(child, succession_type, gender_law,
                                                    parent_death_date, visited, allow_bastards)
                if next_heir:
                    return next_heir

        # 5. If no child, check the relevant parent line
        parent = self.get_relevant_parent(ruler, gender_law)
        if parent:
            if self.is_alive_at(parent, parent_death_date):
                return parent
            else:
                return self.find_heir_primoultimo(parent, succession_type, gender_law,
                                                parent_death_date, visited, allow_bastards)

        # 6. None found
        return None

    ###########################################
    # Checking Validity, Date Comparisons
    ###########################################

    def is_valid_by_gender_law(self, character, gender_law):
        """
        Return True if the character meets the gender law:
          - AGNATIC: only males
          - ENATIC: only females
          - AGNATIC_COGNATIC: male first, then female => but we handle 'male first' in ordering. 
            For a simple filter, we keep all. The ordering is done at the point of searching. 
            But if we want to be strict, we do keep both. 
            Actually, it's simpler to say we always 'keep' them but rely on the logic that tries men first, then women. 
            For the new approach, though, we separate them in code. 
            So for a single pass filter, we won't exclude the female if the law allows fallback. 
            Typically you want the code that picks the order to do the partition. 
            But to keep it easy, let's do a minimal approach:
        """
        if gender_law == GenderLaw.AGNATIC:       
            return (not character.female)
        elif gender_law == GenderLaw.ENATIC:
            return character.female
        elif gender_law == GenderLaw.ABSOLUTE_COGNATIC:
            return True  # everyone
        elif gender_law == GenderLaw.AGNATIC_COGNATIC:
            return True  # keep everyone, we do the male-first or female fallback in the search ordering
        elif gender_law == GenderLaw.ENATIC_COGNATIC:
            return True
        return True

    def get_relevant_parent(self, ruler, gender_law):
        """
        Return father or mother depending on the gender law. 
        If absolute_cognatic, we keep it simple and pick father.
        """
        if ruler is None:
            return None
        # father or mother ID
        if gender_law in [GenderLaw.AGNATIC, GenderLaw.AGNATIC_COGNATIC, GenderLaw.ABSOLUTE_COGNATIC]:
            parent_id = ruler.father
        else:
            # Enatic or Enatic-Cognatic
            parent_id = ruler.mother

        return self.characters.get(parent_id) if parent_id in self.characters else None

    def is_alive_at(self, character, date_tuple):
        """
        Return True if 'character' was alive on 'date_tuple' (year,month,day).
        - If character died in or before that date, return False
        - If no death date, they're effectively alive in that context
        """
        if character.death_year is None:
            return True
        c_death = self.get_death_date(character)  # (dy,dm,dd)
        return c_death > date_tuple

    def was_alive_or_posthumous(self, character, parent_death_date):
        """
        For Seniority or other checks, we want to see if the character 
        wasn't disqualified by parent's death date. 
        A simpler approach is to see if the character was at least born 
        before or on that date. (Dead or alive is separate.)
        """
        c_birth = self.get_birth_date(character)
        # Must be born on or before parent's death date to be considered.
        if c_birth > parent_death_date:
            return False
        return True

    ###########################################
    # Existing Utility Methods (dates, printing)
    ###########################################

    def get_birth_date(self, person):
        return (
            person.birth_year or 0,
            person.birth_month or 1,
            person.birth_day or 1
        )

    def get_death_date(self, person):
        """
        Assume characters without death dates die far in the future 
        so they're effectively 'alive' unless we compare a date beyond 9999
        """
        return (
            person.death_year or 9999,
            person.death_month or 12,
            person.death_day or 31
        )

    def get_children_in_birth_order(self, parent_id):
        # Just do a quick lookup instead of scanning the entire dict
        children = self.parent_to_children.get(parent_id, [])
        return sorted(children, key=lambda c: (
            c.birth_year or 0, 
            c.birth_month or 1, 
            c.birth_day or 1
        ))

    def convert_to_ingame_date(self, year):
        """Convert the year into T.A. or S.A. format based on cutoff points."""
        if isinstance(year, int) or (isinstance(year, str) and year.isdigit()):
            year = int(year)
            if year > 4033:
                return f"T.A. {year - 4033}"  # Fourth Age
            elif 592 < year <= 4033:
                return f"F.A. {year - 592}"  # Third Age
            else:
                return f"S.A. {year}"        # Second Age fallback
        return "?"

    def print_title_histories(self):
        """Print each dynasty's rulers to the console with in-game formatted dates."""
        for dynasty, rulers in self.titles.items():
            print(f"\n--- Dynasty: {dynasty} ---")
            for ruler_id, by, bm, bd, dy, dm, dd in rulers:
                inherited = f"{self.convert_to_ingame_date(by)}.{bm:02}.{bd:02}"
                died = f"{self.convert_to_ingame_date(dy)}.{dm:02}.{dd:02}"
                print(f"Ruler: {ruler_id} | Inherited: {inherited} | Died: {died}")
        print("\n")

    def write_title_histories_to_file(self):
        """
        Output the collected data (self.titles) to a file, 
        in the style of placeholder_title blocks.
        """
        from ck3gen.paths import CHARACTER_OUTPUT_DIR
        CHARACTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = CHARACTER_OUTPUT_DIR / 'title_history.txt'

        with open(output_path, 'w', encoding='utf-8') as file:
            for dynasty, rulers in self.titles.items():
                # Write the placeholder_title header
                file.write("placeholder_title = {\n")
                
                placeholder_title = {}
                
                for ruler_data in rulers:
                    # ruler_data = (ruler_id, by, bm, bd, dy, dm, dd)
                    ruler_id, by, bm, bd, dy, dm, dd = ruler_data
                    # Find the ruler’s name
                    if ruler_id in self.characters:
                        ruler_name = self.characters[ruler_id].name
                    else:
                        ruler_name = "Unknown"

                    # Add ruler to the dynasty's placeholder_title
                    date_string = f"{by:04}.{bm:02}.{bd:02}"
                    placeholder_title[date_string] = {
                        "holder": f"{ruler_id}"
                    }

                    # If there's a next ruler, mark the previous ruler's end date
                    idx = rulers.index(ruler_data)
                    if idx + 1 < len(rulers):
                        next_ruler = rulers[idx + 1]
                        next_start_year, next_start_month, next_start_day = next_ruler[1], next_ruler[2], next_ruler[3]
                        next_holder_id = next_ruler[0]
                        next_name = self.characters[next_holder_id].name if next_holder_id in self.characters else "Unknown"
                        placeholder_title[f"{next_start_year:04}.{next_start_month:02}.{next_start_day:02}"] = {
                            "holder": f"{next_holder_id} #{next_name}"
                        }

                # Write placeholder_title entries to the file
                for date, entry in placeholder_title.items():
                    file.write(f"    {date} = {{\n")
                    file.write(f"        holder = {entry['holder']}\n")
                    file.write("    }\n")
                
                file.write("}\n\n")  # Close the placeholder_title block and add blank line