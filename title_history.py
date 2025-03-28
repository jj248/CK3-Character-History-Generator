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

        # Ensure the deceased character has a death date
        if not deceased_character.death_year or not deceased_character.death_month or not deceased_character.death_day:
            logging.warning(f"Deceased character {deceased_character.char_id} does not have a complete death date. Skipping title transfer.")
            return

        death_date = f"{deceased_character.death_year}.{deceased_character.death_month:02}.{deceased_character.death_day:02}"
        last_holder = list(self.titles[dynasty].values())[-1]["holder"] if self.titles[dynasty] else None

        if new_holder:
            # Assign new holder only after the previous holder has died
            self.titles[dynasty][death_date] = {"holder": new_holder.char_id}
            logging.info(f"Title for dynasty {dynasty} inherited by {new_holder.char_id} on {death_date}.")
        elif last_holder != 0:  # Only add `holder = 0` if it's not already 0
            self.titles[dynasty][death_date] = {"holder": 0}
            logging.warning(f"Title for dynasty {dynasty} has no heirs on {death_date}.")


    def find_new_heir(self, deceased_character):
        gender_law = deceased_character.gender_law
        male_heirs = [c for c in deceased_character.children if c.alive and c.sex == "Male" and c.dynasty == deceased_character.dynasty]
        female_heirs = [c for c in deceased_character.children if c.alive and c.sex == "Female" and c.dynasty == deceased_character.dynasty]

        if not male_heirs and not female_heirs:
            cousins = []
            
            # Find first cousins (siblings of the deceased character's parents)
            for parent in [deceased_character.father, deceased_character.mother]:
                if parent:  # Ensure the parent exists
                    for sibling in parent.children:  # Get the parent's siblings
                        if sibling != deceased_character:  # Skip the deceased character
                            cousins.extend([c for c in sibling.children if c.alive and c.dynasty == deceased_character.dynasty])

            # Only populate second_cousins if no cousins were found
            second_cousins = []
            if not cousins:
                # Find second cousins (children of cousins)
                for cousin in cousins:
                    for cousin_child in cousin.children:  # Get the cousin's children
                        if cousin_child.alive and cousin_child.dynasty == deceased_character.dynasty:
                            second_cousins.append(cousin_child)

            # Only populate third_cousins if no second_cousins were found
            third_cousins = []
            if not second_cousins:
                # Find third cousins (children of second cousins)
                for cousin in second_cousins:
                    for cousin_child in cousin.children:  # Get the cousin's children
                        if cousin_child.alive and cousin_child.dynasty == deceased_character.dynasty:
                            third_cousins.append(cousin_child)

            # Only populate fourth_cousins if no third_cousins were found
            fourth_cousins = []
            if not third_cousins:
                # Find fourth cousins (children of third cousins)
                for cousin in third_cousins:
                    for cousin_child in cousin.children:  # Get the cousin's children
                        if cousin_child.alive and cousin_child.dynasty == deceased_character.dynasty:
                            fourth_cousins.append(cousin_child)

            # Only populate fifth_cousins if no fourth_cousins were found
            fifth_cousins = []
            if not fourth_cousins:
                # Find fifth cousins (children of fourth cousins)
                for cousin in fourth_cousins:
                    for cousin_child in cousin.children:  # Get the cousin's children
                        if cousin_child.alive and cousin_child.dynasty == deceased_character.dynasty:
                            fifth_cousins.append(cousin_child)
            
            # Only populate sixth_cousins if no fifth_cousins were found
            sixth_cousins = []
            if not fifth_cousins:
                # Find fifth cousins (children of fourth cousins)
                for cousin in fifth_cousins:
                    for cousin_child in cousin.children:  # Get the cousin's children
                        if cousin_child.alive and cousin_child.dynasty == deceased_character.dynasty:
                            sixth_cousins.append(cousin_child)
            
            # Only populate seventh_cousins if no sixth_cousins were found
            seventh_cousins = []
            if not sixth_cousins:
                # Find fifth cousins (children of fourth cousins)
                for cousin in sixth_cousins:
                    for cousin_child in cousin.children:  # Get the cousin's children
                        if cousin_child.alive and cousin_child.dynasty == deceased_character.dynasty:
                            seventh_cousins.append(cousin_child)

            # Combine male heirs, cousins, second cousins, third cousins, fourth cousins, and fifth cousins
            male_heirs += cousins + second_cousins + third_cousins + fourth_cousins + fifth_cousins + sixth_cousins + seventh_cousins
            female_heirs += cousins + second_cousins + third_cousins + fourth_cousins + fifth_cousins + sixth_cousins + seventh_cousins


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
            # Check if the deceased character is the current title holder
            current_holder_id = list(self.titles[dynasty].values())[-1]["holder"] if self.titles[dynasty] else None
            
            # If the deceased character is the current holder, we need to update the title
            if current_holder_id == deceased_character.char_id:
                new_heir = self.find_new_heir(deceased_character)
                self.update_holder(deceased_character, new_heir)
            else:
                # Check if the deceased character is an heir or could have been in line for succession
                potential_heir = self.find_new_heir(deceased_character)
                if potential_heir and potential_heir.char_id == deceased_character.char_id:
                    # If the deceased character was an heir, update the title
                    self.update_holder(deceased_character, potential_heir)


    def export_title_history(self, filename="title_history.txt"):
        with open(filename, "w", encoding="utf-8") as file:
            for dynasty, history in self.titles.items():
                file.write(f"{dynasty} = {{\n")
                for date, data in history.items():
                    file.write(f"    {date} = {{\n        holder = {data['holder']}\n    }}\n")
                file.write("}\n\n")
        logging.info(f"Title history exported to {filename}.")
