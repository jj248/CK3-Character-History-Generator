import logging
import random  # Import random module for selecting a random character
from collections import OrderedDict

class TitleHistory:
    def __init__(self, characters):
        self.titles = {}  # Dictionary to store title histories per dynasty
        self.characters = characters

    def assign_initial_holder(self, character):
        dynasty = character.dynasty
        if not dynasty:
            logging.warning(f"Character {character.char_id} has no dynasty. Skipping title assignment.")
            return

        if dynasty not in self.titles:
            self.titles[dynasty] = OrderedDict()

        birth_date = f"{character.birth_year}.{character.birth_month:02}.{character.birth_day:02}"
        self.titles[dynasty][birth_date] = {"holder": character.char_id, "date": birth_date}  # Add "date" key

    def update_holder(self, deceased_character, new_holder):
        dynasty = deceased_character.dynasty
        if not dynasty or dynasty not in self.titles:
            return

        # Ensure the deceased character has a death date
        if not deceased_character.death_year or not deceased_character.death_month or not deceased_character.death_day:
            logging.warning(f"Deceased character {deceased_character.char_id} does not have a complete death date. Skipping title transfer.")
            return

        # Find the previous holder in the dynasty (last one before the deceased)
        last_entry = list(self.titles[dynasty].values())[-1] if self.titles[dynasty] else None
        if not last_entry:
            logging.warning(f"No previous holder found for dynasty {dynasty}. Skipping title transfer.")
            return

        last_holder_id = last_entry["holder"]
        last_death_date = last_entry["date"]

        # If the last holder is the same as the deceased, use the deceased's death date to transfer
        if last_holder_id == deceased_character.char_id:
            death_date = f"{deceased_character.death_year}.{deceased_character.death_month:02}.{deceased_character.death_day:02}"
        else:
            death_date = last_death_date  # Use the previous holder's death date

        # Transfer the title to the new holder
        if new_holder:
            self.titles[dynasty][death_date] = {"holder": new_holder.char_id, "date": death_date}
        elif last_holder_id != 0:  # Only add `holder = 0` if it's not already 0
            self.titles[dynasty][death_date] = {"holder": 0, "date": death_date}



    def find_new_heir(self, deceased_character):
        gender_law = deceased_character.gender_law
        
        male_heirs = [c for c in deceased_character.children if c.alive and c.sex == "Male" and c.dynasty == deceased_character.dynasty and not c.is_bastard]
        female_heirs = [c for c in deceased_character.children if c.alive and c.sex == "Female" and c.dynasty == deceased_character.dynasty and not c.is_bastard]

        # Check spouses as potential heirs
        spouse = deceased_character.spouse
        if spouse and spouse.alive and spouse.dynasty == deceased_character.dynasty and not spouse.is_bastard:
            male_heirs.append(spouse) if spouse.sex == "Male" else female_heirs.append(spouse)
        
        if not male_heirs and not female_heirs:
            closely_related_members = [
                c for c in self.characters
                if c.dynasty == deceased_character.dynasty and c.alive and not c.is_bastard and
                (c in deceased_character.children or c in [deceased_character.father, deceased_character.mother] or c in deceased_character.siblings())
            ]
            male_heirs.extend([c for c in closely_related_members if c.sex == "Male"])
            female_heirs.extend([c for c in closely_related_members if c.sex == "Female"])

        if not male_heirs and not female_heirs:
            # Find extended family: cousins, second cousins, etc.
            extended_family = self.find_extended_family(deceased_character)
            male_heirs.extend([c for c in extended_family if c.sex == "Male"])
            female_heirs.extend([c for c in extended_family if c.sex == "Female"])

        if not male_heirs and not female_heirs:
            # Check for bastards if no other heirs are found
            all_bastards = [
                c for c in self.characters if c.dynasty == deceased_character.dynasty and c.alive and c.is_bastard
            ]
            if all_bastards:
                selected_bastard = random.choice(all_bastards)
                if selected_bastard.sex == "Male":
                    male_heirs.append(selected_bastard)
                else:
                    female_heirs.append(selected_bastard)

        if not male_heirs and not female_heirs:
            # Find a female member of the dynasty married into another dynasty
            married_dynasty_members = [
                c for c in self.characters if c.dynasty == deceased_character.dynasty and c.alive and
                c.sex == "Female" and c.spouse and c.spouse.dynasty != deceased_character.dynasty and c.age > 18 and c.children
            ]
            if married_dynasty_members:
                selected_married_female = random.choice(married_dynasty_members)
                female_heirs.append(selected_married_female)

        if not male_heirs and not female_heirs:
            all_living_members = [
                c for c in self.characters if c.dynasty == deceased_character.dynasty and c.alive and not c.is_bastard
            ]
            if all_living_members:
                selected_member = random.choice(all_living_members)
                if selected_member.sex == "Male":
                    male_heirs.append(selected_member)
                else:
                    female_heirs.append(selected_member)

        if gender_law == "male" and male_heirs:
            return sorted(male_heirs, key=lambda c: c.birth_year)[0]
        if gender_law == "female" and female_heirs:
            return sorted(female_heirs, key=lambda c: c.birth_year)[0]
        if gender_law == "equal":
            all_heirs = male_heirs + female_heirs
            if all_heirs:
                return sorted(all_heirs, key=lambda c: c.birth_year)[0]

        return None  # No heirs found within the dynasty

    def process_death(self, deceased_character):
        if not deceased_character.death_year:
            logging.warning(f"Death year missing for {deceased_character.char_id}. Using current simulation year.")
            deceased_character.death_year = self.get_current_simulation_year()

        dynasty = deceased_character.dynasty
        if dynasty and dynasty in self.titles:
            current_holder_entry = max(self.titles[dynasty].values(), key=lambda x: x.get("date", ""))
            current_holder_id = current_holder_entry["holder"] if current_holder_entry else None

            new_heir = self.find_new_heir(deceased_character)
            if current_holder_id == deceased_character.char_id or (new_heir and new_heir.char_id == deceased_character.char_id):
                if new_heir:
                    self.update_holder(deceased_character, new_heir)
                else:
                    logging.warning(f"No heir found for {deceased_character.char_id}. Title might be contested.")

    def export_title_history(self, filename="title_history.txt"):
        with open(filename, "w", encoding="utf-8") as file:
            for dynasty, history in self.titles.items():
                file.write(f"{dynasty} = {{\n")
                for date, data in history.items():
                    file.write(f"    {date} = {{\n        holder = {data['holder']}\n    }}\n")
                file.write("}\n\n")
        logging.info(f"Title history exported to {filename}.")

    def find_extended_family(self, character, max_generations=5):
        # A more complex function to go several generations back and check each level of family for heirs.
        family_members = []
        generation = 0
        current_generation = [character]
        while generation < max_generations:
            next_generation = []
            for member in current_generation:
                next_generation.extend(member.siblings())  # Add siblings of the current generation
            family_members.extend(next_generation)
            current_generation = next_generation
            generation += 1
        return family_members
