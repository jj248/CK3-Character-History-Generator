import logging
from collections import OrderedDict

class TitleHistory:
    def __init__(self):
        self.titles = {}  # Dictionary to store title histories per dynasty

    def assign_initial_holder(self, character):
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
        dynasty = deceased_character.dynasty
        if not dynasty or dynasty not in self.titles:
            return

        death_date = f"{deceased_character.death_year}.{deceased_character.death_month:02}.{deceased_character.death_day:02}"
        last_holder = list(self.titles[dynasty].values())[-1]["holder"] if self.titles[dynasty] else None

        if new_holder:
            self.titles[dynasty][death_date] = {"holder": new_holder.char_id}
            logging.info(f"Title for dynasty {dynasty} inherited by {new_holder.char_id} on {death_date}.")
        elif last_holder != 0:  # Only add `holder = 0` if it's not already 0
            self.titles[dynasty][death_date] = {"holder": 0}
            logging.warning(f"Title for dynasty {dynasty} has no heirs on {death_date}.")

    def find_new_heir(self, deceased_character):
        gender_law = deceased_character.gender_law
        male_heirs = [c for c in deceased_character.children if c.alive and c.sex == "Male" and c.dynasty == deceased_character.dynasty]
        female_heirs = [c for c in deceased_character.children if c.alive and c.sex == "Female" and c.dynasty == deceased_character.dynasty]

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
            new_heir = self.find_new_heir(deceased_character)
            self.update_holder(deceased_character, new_heir)

    def export_title_history(self, filename="title_history.txt"):
        with open(filename, "w", encoding="utf-8") as file:
            for dynasty, history in self.titles.items():
                file.write(f"{dynasty} = {{\n")
                for date, data in history.items():
                    file.write(f"    {date} = {{\n        holder = {data['holder']}\n    }}\n")
                file.write("}\n\n")
        logging.info(f"Title history exported to {filename}.")
