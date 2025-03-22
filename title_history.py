import logging
from collections import OrderedDict

class TitleHistory:
    def __init__(self):
        self.titles = {}  # Dictionary to store title histories per dynasty

    def assign_initial_holder(self, character):
        """Assign the first character as the initial title holder for their dynasty."""
        dynasty = character.dynasty
        if not dynasty:
            logging.warning(f"Character {character.char_id} has no dynasty. Skipping title assignment.")
            return

        if dynasty not in self.titles:
            self.titles[dynasty] = OrderedDict()

        birth_date = f"{character.birth_year}.{character.birth_month:02}.{character.birth_day:02}"
        self.titles[dynasty][birth_date] = {"holder": character.char_id}
        logging.info(f"Title for dynasty {dynasty} assigned to {character.char_id} on {birth_date}.")

    def update_holder(self, deceased_character, new_holder):
        """Updates the title holder for the deceased character's dynasty."""
        dynasty = deceased_character.dynasty
        if not dynasty or dynasty not in self.titles:
            return

        death_date = f"{deceased_character.death_year}.{deceased_character.death_month:02}.{deceased_character.death_day:02}"
        
        if new_holder:
            self.titles[dynasty][death_date] = {"holder": new_holder.char_id}
            logging.info(f"Title for dynasty {dynasty} inherited by {new_holder.char_id} on {death_date}.")
        else:
            self.titles[dynasty][death_date] = {"holder": 0}
            logging.warning(f"Title for dynasty {dynasty} has no heirs on {death_date}.")

    def find_new_heir(self, deceased_character):
        """Finds the next heir based on gender law and closest relation."""
        gender_law = deceased_character.gender_law  # male, female, or equal

        # Prioritize children based on gender law
        male_heirs = [c for c in deceased_character.children if c.alive and c.sex == "Male"]
        female_heirs = [c for c in deceased_character.children if c.alive and c.sex == "Female"]

        if gender_law == "male":
            if male_heirs:
                return sorted(male_heirs, key=lambda c: c.birth_year)[0]
            if female_heirs:
                return self.find_female_heir(deceased_character)
        elif gender_law == "female":
            if female_heirs:
                return sorted(female_heirs, key=lambda c: c.birth_year)[0]
            if male_heirs:
                return self.find_male_heir(deceased_character)
        else:  # gender_law == "equal"
            all_heirs = male_heirs + female_heirs
            if all_heirs:
                return sorted(all_heirs, key=lambda c: c.birth_year)[0]

        return self.find_heir_through_intermarriage(deceased_character)

    def find_female_heir(self, deceased_character):
        """Finds the closest female heir if no male heirs exist."""
        extended_family = self.get_extended_family(deceased_character)
        female_heirs = [c for c in extended_family if c.alive and c.sex == "Female"]
        return sorted(female_heirs, key=lambda c: c.birth_year)[0] if female_heirs else None

    def find_male_heir(self, deceased_character):
        """Finds the closest male heir if no female heirs exist."""
        extended_family = self.get_extended_family(deceased_character)
        male_heirs = [c for c in extended_family if c.alive and c.sex == "Male"]
        return sorted(male_heirs, key=lambda c: c.birth_year)[0] if male_heirs else None

    def get_extended_family(self, character):
        """Finds extended family members (siblings, uncles, cousins) for inheritance."""
        family = []
        if character.father:
            family.extend(character.father.children)  # Siblings
            if character.father.father:
                family.extend(character.father.father.children)  # Uncles & Aunts
        if character.mother:
            family.extend(character.mother.children)
            if character.mother.father:
                family.extend(character.mother.father.children)
        return family

    def find_heir_through_intermarriage(self, deceased_character):
        """Search through extended family for an heir if the direct line dies out."""
        ancestors = [deceased_character.father, deceased_character.mother]
        while ancestors:
            parent = ancestors.pop()
            if not parent:
                continue
            for sibling in parent.children:
                if sibling.dynasty != deceased_character.dynasty and sibling.alive:
                    return sibling  # Prioritize intermarried dynasties
                ancestors.append(sibling)
        return None  # No valid heirs found
    
    def process_death(self, deceased_character):
        """Handles inheritance when a title holder dies."""
        if not deceased_character.death_year:
            logging.warning(f"Death year missing for {deceased_character.char_id}. Using current simulation year.")
            deceased_character.death_year = self.get_current_simulation_year()

        dynasty = deceased_character.dynasty
        if dynasty and dynasty in self.titles:
            new_heir = self.find_new_heir(deceased_character)
            self.update_holder(deceased_character, new_heir)

    def export_title_history(self, filename="title_history.txt"):
        """Exports the title history to a file."""
        with open(filename, "w", encoding="utf-8") as file:
            for dynasty, history in self.titles.items():
                file.write(f"{dynasty} = {{\n")
                for date, data in history.items():
                    file.write(f"    {date} = {{\n        holder = {data['holder']}\n    }}\n")
                file.write("}\n\n")
        logging.info(f"Title history exported to {filename}.")
