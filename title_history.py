import logging
from collections import OrderedDict

class TitleHistory:
    def __init__(self, title_name="title_name"):
        self.title_name = title_name
        self.history = OrderedDict()
        self.current_holder = None

    def assign_initial_holder(self, character):
        """Assign the first character as the initial title holder."""
        self.current_holder = character
        birth_date = f"{character.birth_year}.{character.birth_month:02}.{character.birth_day:02}"
        self.history[birth_date] = {"holder": character.char_id}
        logging.info(f"Title {self.title_name} assigned to {character.char_id} on {birth_date}.")

    def update_holder(self, deceased_character, new_holder):
        """Updates the title holder when the current holder dies."""
        death_date = f"{deceased_character.death_year}.{deceased_character.death_month:02}.{deceased_character.death_day:02}"

        
        if new_holder:
            self.history[death_date] = {"holder": new_holder.char_id}
            self.current_holder = new_holder
            logging.info(f"Title {self.title_name} inherited by {new_holder.char_id} on {death_date}.")
        else:
            # No heir found, title becomes vacant
            self.history[death_date] = {"holder": 0}
            self.current_holder = None
            logging.warning(f"Title {self.title_name} has no heirs on {death_date}.")

    def find_new_heir(self, deceased_character):
        """Finds the next heir based on oldest-child succession."""
        children = sorted(deceased_character.children, key=lambda c: c.birth_year)
        for child in children:
            if child.alive:
                return child  # Oldest living child inherits
        
        # If no direct heir, check extended family through intermarriage
        return self.find_heir_through_intermarriage(deceased_character)

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

        if self.current_holder and self.current_holder == deceased_character:
            new_heir = self.find_new_heir(deceased_character)
            self.update_holder(deceased_character, new_heir)


    def export_title_history(self, filename="title_history.txt"):
        """Exports the title history to a file."""
        with open(filename, "w", encoding="utf-8") as file:
            file.write(f"{self.title_name} = {{\n")
            for date, data in self.history.items():
                file.write(f"    {date} = {{\n        holder = {data['holder']}\n    }}\n")
            file.write("}\n")
        logging.info(f"Title history exported to {filename}.")
