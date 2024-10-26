import random
import logging
from character import Character
from utils import generate_random_date, generate_char_id
from name_loader import NameLoader

class Simulation:
    def __init__(self, config, name_loader):
        self.config = config
        self.name_loader = name_loader
        self.current_char_id = self.config['initialization']['initialCharID']
        self.character_count = 0
        self.dynasty_char_counters = {}
        self.all_characters = []
        self.character_pool = {}
        self.unmarried_males = {}
        self.unmarried_females = {}
        self.couple_last_child_year = {}  # Tracks last child year for each couple
        self.marriage_max_age_diff = self.config['life_stages'].get('marriageMaxAgeDifference', 5)

    def add_character_to_pool(self, character):
        if character.birth_year not in self.character_pool:
            self.character_pool[character.birth_year] = []
        self.character_pool[character.birth_year].append(character)

    def remove_from_unmarried_pools(self, character):
        age = character.age
        pool = self.unmarried_males if character.sex == 'Male' else self.unmarried_females
        if age in pool and character in pool[age]:
            pool[age].remove(character)

    def update_unmarried_pools(self, year):
        for character in self.all_characters:
            if character.alive and not character.married and character.can_marry:
                age = character.age
                # Ensure age is within the bounds of the marriageRates list
                if age >= len(self.config['life_stages']['marriageRates'][character.sex]):
                    continue  # Skip if age is beyond the configured rates
                marriage_rate = self.config['life_stages']['marriageRates'][character.sex][age]
                if marriage_rate > 0 and random.random() < marriage_rate:
                    pool = self.unmarried_males if character.sex == 'Male' else self.unmarried_females
                    if age not in pool:
                        pool[age] = []
                    if character not in pool[age]:
                        pool[age].append(character)


    def character_death_check(self, character):
        age = character.age
        sex = character.sex

        if age < 0 or age > 120:
            age = max(0, min(age, 120))

        mortality_rates = self.config['life_stages']['mortalityRates'][sex]

        if 1 > age:
            mortality_rate = 0 # Always ensure they're at least 1 yr old to make sure we don't have deaths before births
        elif 1 <= age < len(mortality_rates):
            mortality_rate = mortality_rates[age]
        else:
            mortality_rate = 1.0  # 100% chance of death

        return random.random() < mortality_rate

    def marry_characters(self, char1, char2, year):
        if char1.char_id == char2.char_id:
            logging.info(f"Attempted self-marriage for {char1.char_id}. Skipping.")
            return
			
        if char1.married or char2.married:
            logging.info(f"One of the characters is already married: {char1.char_id}, {char2.char_id}. Skipping.")
            return
		
        if not char1.alive or not char2.alive:
            return

        if char1.death_year and char1.death_year <= year:
            return
        if char2.death_year and char2.death_year <= year:
            return

        # Prevent sibling marriages
        if self.are_siblings(char1, char2):
            logging.info(f"Preventing sibling marriage between {char1.char_id} and {char2.char_id}.")
            return

        # Determine marriage holder based on gender laws
        if char1.gender_law == "male" and char1.sex == "Male":
            marriage_holder = char1
            spouse = char2
            marriage_type = "add_spouse"
            children_dynasty = char1.dynasty
        elif char1.gender_law == "female" and char1.sex == "Female":
            marriage_holder = char1
            spouse = char2
            marriage_type = "add_matrilineal_spouse"
            children_dynasty = char1.dynasty
        elif char1.gender_law == "equal":
            if random.random() < 0.5:
                marriage_holder = char1
                spouse = char2
                marriage_type = "add_spouse" if char1.sex == "Male" else "add_matrilineal_spouse"
                children_dynasty = char1.dynasty
            else:
                marriage_holder = char2
                spouse = char1
                marriage_type = "add_spouse" if char2.sex == "Male" else "add_matrilineal_spouse"
                children_dynasty = char2.dynasty
        else:
            marriage_holder = char1 if char1.sex == "Male" else char2
            spouse = char2 if marriage_holder == char1 else char1
            marriage_type = "add_spouse" if marriage_holder.sex == "Male" else "add_matrilineal_spouse"
            children_dynasty = marriage_holder.dynasty

        # Prioritize marrying candidates from other dynasties
        if marriage_holder.dynasty and spouse.dynasty and marriage_holder.dynasty == spouse.dynasty:
            # Already handled by sibling check; proceed to marry
            pass

        # Update marital status
        char1.married = True
        char1.spouse = char2
        char2.married = True
        char2.spouse = char1

        # Remove from unmarried pools
        self.remove_from_unmarried_pools(char1)
        self.remove_from_unmarried_pools(char2)

        # Record marriage event
        marriage_date = generate_random_date(year)

        # Ensure marriage date is before death dates
        marriage_year = int(marriage_date.split('.')[0])
        if (char1.death_year and marriage_year >= char1.death_year) or \
           (char2.death_year and marriage_year >= char2.death_year):
            return  # Do not record marriage if it occurs after death

        marriage_holder.add_event(marriage_date, f"{marriage_type} = {spouse.char_id}")

    def create_child(self, mother, father, birth_year):
        # Enforce maximum number of children per woman
        maximum_children = self.config['life_stages']['maximumNumberOfChildren']
        if len(mother.children) >= maximum_children:
            logging.info(f"{mother.char_id} has reached the maximum number of children ({maximum_children}).")
            return None

        # Enforce minimum years between children
        couple_key = (father.char_id, mother.char_id)
        last_birth_year = self.couple_last_child_year.get(couple_key, None)
        min_years = self.config['life_stages']['minimumYearsBetweenChildren']

        # Use fertilityRates to determine if a child is produced
        female_age = mother.age
        fertility_rate = self.config['life_stages']['fertilityRates']['Female'][female_age]

        # Proceed with child creation
        self.character_count += 1

        child_generation = max(mother.generation, father.generation) + 1

        if child_generation > self.config['initialization']['generationMax']:
            return None  # Do not create child

        child_sex = "Male" if random.random() < 0.5 else "Female"

        # Determine dynasty and culture based on marriage laws and parents
        if mother.gender_law == 'male' and father.gender_law == 'male':
            child_dynasty = father.dynasty
            child_culture = father.culture
            child_religion = father.religion
            child_gender_law = father.gender_law
        elif mother.gender_law == 'female' and mother.sex == "Female":
            child_dynasty = mother.dynasty
            child_culture = mother.culture
            child_religion = mother.religion
            child_gender_law = mother.gender_law
        else:
            if random.random() < 0.5:
                child_dynasty = father.dynasty
                child_culture = father.culture
                child_religion = father.religion
                child_gender_law = father.gender_law
            else:
                child_dynasty = mother.dynasty
                child_culture = mother.culture
                child_religion = mother.religion
                child_gender_law = mother.gender_law

        # Handle lowborn characters (dynasty can be None)
        dynasty_prefix = child_dynasty.split('_')[1] if child_dynasty and '_' in child_dynasty else "lowborn"

        child_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)
        
		# Assign name based on inheritance chances
        child_name = self.assign_child_name(child_sex, mother, father, child_dynasty)
		
        sexuality_distribution = self.config['skills_and_traits']['sexualityDistribution']

        child = Character(
            char_id=child_char_id,
            name=child_name,
            sex=child_sex,
            birth_year=birth_year,
            dynasty=child_dynasty,
            culture=child_culture,
            religion=child_religion,
            gender_law=child_gender_law,
            sexuality_distribution=sexuality_distribution,
            generation=child_generation
        )

        # Set parents
        child.father = father if father.sex == 'Male' else mother
        child.mother = mother if mother.sex == 'Female' else father

        # Add child to parents' children
        mother.children.append(child)
        father.children.append(child)

        # Assign skills, education, and personality traits
        child.assign_skills(self.config['skills_and_traits']['skillProbabilities'])
        child.assign_education(self.config['skills_and_traits']['educationProbabilities'])
        child.assign_personality_traits(self.config['skills_and_traits']['personalityTraits'])

        # Update last child birth year
        self.couple_last_child_year[couple_key] = birth_year

        return child
		
    def assign_child_name(self, child_sex, mother, father, child_dynasty):
		# Fetch dynasty config
        dynasties = self.config.get('initialization', {}).get('dynasties', [])
        current_dynasty = None
        for dyn in dynasties:
            if dyn['dynastyID'] == child_dynasty:
                current_dynasty = dyn
                break
	    
        if not current_dynasty:
            logging.warning(f"Dynasty {child_dynasty} not found. Assigning random name.")
            return self.name_loader.load_names(mother.culture, child_sex.lower())
	    
        # Get name inheritance chances
        inheritance_chances = current_dynasty['nameInheritance']
        options = ['grandparent', 'parent', 'none']
        probabilities = [
            inheritance_chances['grandparentNameInheritanceChance'],
            inheritance_chances['parentNameInheritanceChance'],
            inheritance_chances['noNameInheritanceChance']
        ]

        chosen_method = random.choices(options, probabilities)[0]

        if chosen_method == 'grandparent':
            # Assign grandparent's name
            if child_sex == "Male":
                # Paternal grandfather's name
                grandfather = father.father
                if grandfather:
                    assigned_name = grandfather.name
                else:
                    assigned_name = self.name_loader.load_names(father.culture, child_sex.lower())
            elif child_sex == "Female":
                # Maternal grandmother's name
                grandmother = mother.mother
                if grandmother:
                    assigned_name = grandmother.name
                else:
                    assigned_name = self.name_loader.load_names(mother.culture, child_sex.lower())
            # Fallback to random name if grandparent not found
            return self.ensure_unique_name(assigned_name, mother, father, child_sex.lower())

        elif chosen_method == 'parent':
            # Assign parent's name
            if child_sex == "Male":
                assigned_name = father.name
            elif child_sex == "Female":
                assigned_name = mother.name
            return self.ensure_unique_name(assigned_name, mother, father, child_sex.lower())

        else:
            # No inheritance, assign random name
            assigned_name = self.name_loader.load_names(mother.culture, child_sex.lower())
            return self.ensure_unique_name(assigned_name, mother, father, child_sex.lower())
			
    def ensure_unique_name(self, proposed_name, mother, father, child_gender):
        # Gather existing names among living children of both parents
        existing_names = set()
        for child in mother.children + father.children:
            if child.alive:
                existing_names.add(child.name)
    
        if proposed_name not in existing_names:
            return proposed_name
        else:
            #logging.info(f"Duplicate name '{proposed_name}' found among living children of {mother.char_id} and {father.char_id}. Assigning a unique random name.")
            # Assign a random name excluding existing names
            unique_name = self.get_unique_random_name(mother.culture, child_gender, existing_names=existing_names)
            if unique_name:
                logging.debug(f"Assigned unique random name: {unique_name}")
                return unique_name
            else:
                logging.error(f"No available unique names to assign to child of {mother.char_id} and {father.char_id}.")
                return "Unnamed"  # Fallback name
				
    def get_unique_random_name(self, culture, child_sex, existing_names):
        available_names = self.name_loader.get_all_names(culture, child_sex)
        # Exclude existing names
        filtered_names = [name for name in available_names if name not in existing_names]
        
        if not filtered_names:
            logging.error(f"No available unique names left for culture '{culture}' and sex '{child_sex}'.")
            return None  # Or handle as desired
        return random.choice(filtered_names)

    def match_marriages(self, males, females, year):
        # Attempt to marry males with females from other dynasties first
        for male in males:
            if not male.alive or male.married or not male.can_marry:
                continue

            # Find available females from other dynasties
            available_females = [
                f for f in females 
                if f.alive and not f.married and f.can_marry and 
                   (f.dynasty != male.dynasty or f.dynasty is None) and 
                   not self.are_siblings(male, f) and
                   abs(f.age - male.age) <= self.marriage_max_age_diff
            ]

            if available_females:
                female = random.choice(available_females)
                self.marry_characters(male, female, year)
                continue

            # If no females from other dynasties, find from same dynasty
            available_females = [
                f for f in females 
                if f.alive and not f.married and f.can_marry and 
                   (f.dynasty == male.dynasty) and 
                   not self.are_siblings(male, f) and
                   abs(f.age - male.age) <= self.marriage_max_age_diff
            ]

            if available_females:
                female = random.choice(available_females)
                self.marry_characters(male, female, year)
                continue

    def are_siblings(self, char1, char2):
        """Check if two characters are siblings based on shared parents."""
        return (char1.father is not None and char1.father == char2.father) and \
               (char1.mother is not None and char1.mother == char2.mother)
			   
    def handle_bastardy(self, year, bastardy_chance_male, bastardy_chance_female, fertility_rates):
        for character in self.all_characters:
            if not character.alive:
                continue

            if character.sex == "Female":
                # Check if fertility rate is non-zero
                female_age = character.age
                if female_age >= len(fertility_rates['Female']):
                    fertility_rate = 0.0
                else:
                    fertility_rate = fertility_rates['Female'][female_age]

                if fertility_rate == 0.0:
                    continue  # Not fertile

                # Check if already having a child by normal means this year
                couple_key = (character.spouse.char_id, character.char_id) if character.married and character.spouse else None
                if couple_key and self.couple_last_child_year.get(couple_key, -float('inf')) == year:
                    continue  # Already had a child this year

                # Apply bastardy chance
                if random.random() < bastardy_chance_female:
                    # Female has a bastard child
                    child = self.create_bastard_child(character, year, is_male=False)
                    if child:
                        self.add_character_to_pool(child)
                        self.all_characters.append(child)

            elif character.sex == "Male":
                # Apply bastardy chance
                if random.random() < bastardy_chance_male:
                    # Male has a bastard child
                    child = self.create_bastard_child(character, year, is_male=True)
                    if child:
                        self.add_character_to_pool(child)
                        self.all_characters.append(child)

    def create_bastard_child(self, parent, birth_year, is_male):
        maximum_children = self.config['life_stages']['maximumNumberOfChildren']
        # Check if parent has reached maximum number of children
        if len(parent.children) >= maximum_children:
            logging.info(f"{parent.char_id} has reached the maximum number of children ({maximum_children}). Cannot have more bastard children.")
            return None

        # For females, check fertility rate again
        if parent.sex == "Female":
            female_age = parent.age
            fertility_rate = self.config['life_stages']['fertilityRates']['Female'][female_age] if female_age < len(self.config['life_stages']['fertilityRates']['Female']) else 0.0
            if fertility_rate == 0.0:
                return None  # Did not conceive

        # Proceed with child creation
        self.character_count += 1

        child_generation = parent.generation + 1

        if child_generation > self.config['initialization']['generationMax']:
            return None  # Do not create child

        child_sex = "Male" if is_male else "Female"

        # Assign dynasty based on parent
        child_dynasty = parent.dynasty
        child_culture = parent.culture
        child_religion = parent.religion
        child_gender_law = parent.gender_law

        # Handle lowborn characters (dynasty can be None)
        dynasty_prefix = child_dynasty.split('_')[1] if child_dynasty and '_' in child_dynasty else "lowborn"

        child_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)

        # Assign name based on inheritance chances
        if is_male:
            # Bastard male child: no mother
            child_name = self.assign_child_name(
                child_sex=child_sex,
                mother=parent,
                father=parent,
                child_dynasty=child_dynasty
            )
        else:
            # Bastard female child: no father
            child_name = self.assign_child_name(
                child_sex=child_sex,
                mother=parent,
                father=parent,
                child_dynasty=child_dynasty
            )

        sexuality_distribution = self.config['skills_and_traits']['sexualityDistribution']

        child = Character(
            char_id=child_char_id,
            name=child_name,
            sex=child_sex,
            birth_year=birth_year,
            dynasty=child_dynasty,
            culture=child_culture,
            religion=child_religion,
            gender_law=child_gender_law,
            sexuality_distribution=sexuality_distribution,
            generation=child_generation
        )

        # Set parent(s)
        if is_male:
            # Bastard child: father exists, mother is None
            child.father = parent
            child.mother = None
            parent.children.append(child)
        else:
            # Bastard child: mother exists, father is None
            child.mother = parent
            child.father = None
            parent.children.append(child)
			
        # Assign the 'bastard' trait
        child.add_trait('bastard')

        # Assign skills, education, and personality traits
        child.assign_skills(self.config['skills_and_traits']['skillProbabilities'])
        child.assign_education(self.config['skills_and_traits']['educationProbabilities'])
        child.assign_personality_traits(self.config['skills_and_traits']['personalityTraits'])

        logging.info(f"Bastard child {child.char_id} ({child.name}, Age {child.age}) born to {'female' if is_male else 'male'} parent {parent.char_id}.")

        return child

    def run_simulation(self):
        life_stages = self.config['life_stages']
        marriage_rates = life_stages['marriageRates']
        fertility_rates = life_stages['fertilityRates']
        bastardy_chance_male = life_stages['bastardyChanceMale']
        bastardy_chance_female = life_stages['bastardyChanceFemale']
        maximum_children = life_stages['maximumNumberOfChildren']

        for year in range(self.config['initialization']['minYear'], self.config['initialization']['maxYear'] + 1):
            # 1. Update Characters' Ages
            for character in self.all_characters:
                if character.alive:
                    character.age = year - character.birth_year
                    if character.age < 0:
                        character.age = 0
						
            # **Clear unmarried pools after updating ages**
            self.unmarried_males.clear()
            self.unmarried_females.clear()

            # 2. Handle Marriages
            # First, update unmarried pools based on marriage rates
            self.update_unmarried_pools(year)

            # Extract all unmarried males and females
            all_unmarried_males = []
            for age, males in self.unmarried_males.items():
                all_unmarried_males.extend(males)
            all_unmarried_females = []
            for age, females in self.unmarried_females.items():
                all_unmarried_females.extend(females)

            # Proceed to match marriages
            if all_unmarried_males and all_unmarried_females:
                self.match_marriages(all_unmarried_males, all_unmarried_females, year)

            # 3. Handle Births
            for character in self.all_characters:
                if character.alive and character.married and character.sex == "Female":
                    # Check if character has reached maximum number of children
                    if len(character.children) >= maximum_children:
                        continue

                    # Use fertilityRates to determine if a child is produced
                    female_age = character.age
                    fertility_rate = fertility_rates['Female'][female_age]
                    if random.random() < fertility_rate:
                        child = self.create_child(character, character.spouse, year)
                        if child:
                            self.add_character_to_pool(child)
                            self.all_characters.append(child)
							
            # 4. Handle Bastardy
            self.handle_bastardy(year, bastardy_chance_male, bastardy_chance_female, fertility_rates)

            # 5. Assign Skills, Education, and Traits at Age 16
            for character in self.all_characters:
                if character.alive and character.age == 16:
                    character.assign_skills(self.config['skills_and_traits']['skillProbabilities'])
                    character.assign_education(self.config['skills_and_traits']['educationProbabilities'])
                    character.assign_personality_traits(self.config['skills_and_traits']['personalityTraits'])

            # 6. Check for Deaths
            for character in self.all_characters:
                if character.alive:
                    if self.character_death_check(character):
                        character.alive = False
                        character.death_year = year
                        self.remove_from_unmarried_pools(character)
                        death_date = generate_random_date(year)
                        if character.age > 65:
                            death_cause = "death_natural_causes"
                        elif character.age < 18:
                            death_cause = "death_ill"
                        elif character.sex == "Male":
                            death_cause = random.choice([
                                "death_ill",
                                "death_cancer",
                                "death_in_battle",
                                "death_attacked",
                                "death_accident", 
                                "death_murder"
                            ])
                        else:
                            death_cause = random.choice([
                                "death_ill",
                                "death_cancer",
                                "death_accident", 
                                "death_murder"
                            ])							
                        character.add_event(death_date, f"death = {{ death_reason = {death_cause} }}")
                        if character.married and character.spouse.alive:
                            character.spouse.married = False
                            character.spouse.married = None

            # 7. Update Unmarried Pools
            self.update_unmarried_pools(year)

    def export_characters(self, output_filename="family_history.txt"):
        # Initialize the counter
        exported_character_count = 0
		
        with open(output_filename, 'w', encoding='utf-8') as file:
            for character in self.all_characters:
                character_data = character.format_for_export()
                file.write(character_data)
				
				# Increment the counter after each character is written
                exported_character_count += 1
				
        logging.info(f"Character history exported to {output_filename}")
        logging.info(f"Total characters exported: {exported_character_count}")
