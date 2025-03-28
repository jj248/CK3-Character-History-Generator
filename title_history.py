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
        self.titles[dynasty][birth_date] = {"holder": character.char_id}
        # logging.info(f"Title for dynasty {dynasty} assigned to {character.char_id} on {birth_date}.")

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
            # logging.info(f"Title for dynasty {dynasty} inherited by {new_holder.char_id} on {death_date}.")
        elif last_holder != 0:  # Only add `holder = 0` if it's not already 0
            self.titles[dynasty][death_date] = {"holder": 0}
            # logging.warning(f"Title for dynasty {dynasty} has no heirs on {death_date}.")

    def find_new_heir(self, deceased_character):
        gender_law = deceased_character.gender_law
        
        male_heirs = [c for c in deceased_character.children if c.alive and c.sex == "Male" and c.dynasty == deceased_character.dynasty and not c.is_bastard]
        female_heirs = [c for c in deceased_character.children if c.alive and c.sex == "Female" and c.dynasty == deceased_character.dynasty and not c.is_bastard]

        if not male_heirs and not female_heirs:
            # Step 1: Closest relatives first (children, parents, siblings)
            closely_related_members = [
                c for c in self.characters
                if c.dynasty == deceased_character.dynasty and c.alive and not c.is_bastard and
                (c in deceased_character.children or c in [deceased_character.father, deceased_character.mother] or c in deceased_character.siblings())
            ]

            male_heirs.extend([c for c in closely_related_members if c.sex == "Male"])
            female_heirs.extend([c for c in closely_related_members if c.sex == "Female"])

            # Step 2: Look for grandchildren & great-grandchildren
            if not male_heirs and not female_heirs:
                grandchildren = [
                    gc for c in deceased_character.children if c.alive 
                    for gc in c.children if gc.dynasty == deceased_character.dynasty and not gc.is_bastard
                ]
                great_grandchildren = [
                    ggc for gc in grandchildren 
                    for ggc in gc.children if ggc.dynasty == deceased_character.dynasty and not ggc.is_bastard
                ]

                male_heirs.extend([c for c in grandchildren if c.sex == "Male"])
                female_heirs.extend([c for c in grandchildren if c.sex == "Female"])

                male_heirs.extend([c for c in great_grandchildren if c.sex == "Male"])
                female_heirs.extend([c for c in great_grandchildren if c.sex == "Female"])

            # Step 3: Search for cousins (1st-7th, up to 5x removed)
            if not male_heirs and not female_heirs:
                def collect_cousins(starting_relatives, max_cousin_degree=7, max_removals=5):
                    queue = [(cousin, 1, 0) for cousin in starting_relatives]  # (Cousin, Degree, Removal Level)
                    collected_cousins = []
                    processed_cousins = set()  # Set to track already processed cousins

                    while queue:
                        cousin, degree, removals = queue.pop(0)

                        # Skip if we've already processed this cousin
                        if cousin in processed_cousins:
                            continue

                        if degree > max_cousin_degree or removals > max_removals:
                            continue  # Stop at max limit

                        # Mark this cousin as processed
                        processed_cousins.add(cousin)

                        if cousin.dynasty == deceased_character.dynasty and cousin.alive and not cousin.is_bastard:
                            collected_cousins.append(cousin)

                        # Find children (one level removed)
                        for cousin_child in cousin.children:
                            if cousin_child.dynasty == deceased_character.dynasty and cousin_child.alive and not cousin_child.is_bastard:
                                queue.append((cousin_child, degree, removals + 1))

                        # Find siblings of this cousin’s parents (i.e., next-degree cousins)
                        for parent in [cousin.father, cousin.mother]:
                            if parent and parent.father and parent.mother:  # Ensure grandparent exists
                                for sibling in parent.father.children + parent.mother.children:
                                    if sibling != parent:  # Avoid direct parent
                                        for sibling_child in sibling.children:
                                            if sibling_child.dynasty == deceased_character.dynasty and sibling_child.alive and not sibling_child.is_bastard:
                                                queue.append((sibling_child, degree + 1, removals))

                    return collected_cousins

                # Find initial set of cousins (1st cousins)
                starting_cousins = []
                for parent in [deceased_character.father, deceased_character.mother]:
                    if parent:
                        for sibling in parent.siblings():  # Parent's siblings
                            for cousin in sibling.children:  # Their children = 1st cousins
                                if cousin.dynasty == deceased_character.dynasty and cousin.alive and not cousin.is_bastard:
                                    starting_cousins.append(cousin)

                # Collect all cousins up to 7th cousin, 5x removed
                all_cousins = collect_cousins(starting_cousins)

                male_heirs.extend([c for c in all_cousins if c.sex == "Male"])
                female_heirs.extend([c for c in all_cousins if c.sex == "Female"])

        # Step 4: Find the closest living dynasty member
        if not male_heirs and not female_heirs:
            closest_dynasty_members = [
                c for c in self.characters if c.dynasty == deceased_character.dynasty and c.alive and not c.is_bastard
            ]

            # Sort by age
            closest_dynasty_member = None
            if closest_dynasty_members:
                if gender_law == "male":
                    closest_dynasty_member = sorted([c for c in closest_dynasty_members if c.sex == "Male"], key=lambda c: c.birth_year)[0] if [c for c in closest_dynasty_members if c.sex == "Male"] else None
                elif gender_law == "female":
                    closest_dynasty_member = sorted([c for c in closest_dynasty_members if c.sex == "Female"], key=lambda c: c.birth_year)[0] if [c for c in closest_dynasty_members if c.sex == "Female"] else None
                else:  # Equal succession
                    closest_dynasty_member = sorted(closest_dynasty_members, key=lambda c: c.birth_year)[0]

            if closest_dynasty_member:
                if closest_dynasty_member.sex == "Male":
                    male_heirs.append(closest_dynasty_member)
                else:
                    female_heirs.append(closest_dynasty_member)

        # Step 5: If no heir is found, select a random dynasty member
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

        # Step 6: Sorting heirs based on gender law and birth year
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
