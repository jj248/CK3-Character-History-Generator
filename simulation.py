import random
import logging
from character import Character
from utils import generate_random_date, generate_char_id
from name_loader import NameLoader
from title_history import TitleHistory

class Simulation:
    def __init__(self, config, name_loader):
        self.config = config
        self.name_loader = name_loader
        self.current_char_id = self.config['initialization']['initialCharID']
        self.character_count = 0
        self.dynasty_char_counters = {}
        self.title_history = TitleHistory()
        self.all_characters = []
        self.character_pool = {}
        self.unmarried_males = {}
        self.unmarried_females = {}
        self.couple_last_child_year = {}  # Tracks last child year for each couple
        self.marriage_max_age_diff = self.config['life_stages'].get('marriageMaxAgeDifference', 5)
        self.desperation_rates = self.config['life_stages'].get('desperationMarriageRates', {})

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

    def desperation_marriage_check(self, character, year):
        """Check if an unmarried character is willing to marry a lowborn due to desperation."""
        age = character.age
        desperation_chance = self.desperation_rates.get(age, 0)
        
        if random.random() < desperation_chance:
            # Generate a lowborn spouse
            spouse_char_id = generate_char_id("lowborn", self.dynasty_char_counters)
            spouse_name = self.name_loader.load_names(character.culture, "male" if character.sex == "Female" else "female")
            spouse = Character(
                char_id=spouse_char_id,
                name=spouse_name,
                sex="Male" if character.sex == "Female" else "Female",
                birth_year=year - random.randint(18, 40),  # Random adult age
                dynasty=None,  # Lowborn
                is_house=False,
                culture=character.culture,
                religion=character.religion,
                gender_law=character.gender_law,
                sexuality_distribution=self.config['skills_and_traits']['sexualityDistribution'],
                generation=character.generation
            )
            
            # Determine marriage type
            marriage_type = "add_spouse" if character.sex == "Male" else "add_matrilineal_spouse"
            spouse_dynasty = character.dynasty
            
            self.marry_characters(character, spouse, year, marriage_type, spouse_dynasty)
            return True
        return False


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

    def marry_characters(self, char1, char2, year, marriage_type=None, children_dynasty=None):
        if char1.char_id == char2.char_id:
            logging.info(f"Attempted self-marriage for {char1.char_id}. Skipping.")
            return
        
        if char1.married or char2.married:
            logging.info(f"One of the characters is already married: {char1.char_id}, {char2.char_id}. Skipping.")
            return
        
        if not char1.alive or not char2.alive:
            return

        # Assign default marriage type if not already set
        if not marriage_type:
            if char1.gender_law == "male" and char1.sex == "Male":
                marriage_type = "add_spouse"
                children_dynasty = char1.dynasty
            elif char1.gender_law == "female" and char1.sex == "Female":
                marriage_type = "add_matrilineal_spouse"
                children_dynasty = char1.dynasty
            else:
                marriage_type = "add_spouse" if char1.sex == "Male" else "add_matrilineal_spouse"
                children_dynasty = char1.dynasty if char1.dynasty else char2.dynasty

        # Set marital status
        char1.married = True
        char1.spouse = char2
        char2.married = True
        char2.spouse = char1

        # Remove from unmarried pools
        self.remove_from_unmarried_pools(char1)
        self.remove_from_unmarried_pools(char2)

        # Record marriage event
        marriage_date = generate_random_date(year)
        char1.add_event(marriage_date, f"{marriage_type} = {char2.char_id}")

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

        # Track children born per dynasty per generation
        dynasty_gen_count = {}
        for character in self.all_characters:
            if character.alive:
                key = (character.dynasty, character.generation)
                dynasty_gen_count[key] = dynasty_gen_count.get(key, 0) + 1

        # Set a cap per dynasty per generation (adjust as needed)
        dynasty_child_cap = 12  
        if dynasty_gen_count.get((father.dynasty, father.generation), 0) >= dynasty_child_cap:
            logging.info(f"Dynasty {father.dynasty} has reached max children per generation. No more children will be created.")
            return None  # Prevent excess children
        
        # Proceed with child creation
        self.character_count += 1

        child_generation = max(mother.generation, father.generation) + 1

        if child_generation > self.config['initialization']['generationMax']:
            return None  # Do not create child

        child_sex = "Male" if random.random() < 0.5 else "Female"

        # Determine dynasty and culture based on marriage laws and parents
        if mother.gender_law == 'male' and father.gender_law == 'male':
            child_dynasty = father.dynasty
            child_is_house = father.is_house
            child_culture = father.culture
            child_religion = father.religion
            child_gender_law = father.gender_law
        elif mother.gender_law == 'female' and mother.sex == "Female":
            child_dynasty = mother.dynasty
            child_is_house = mother.is_house
            child_culture = mother.culture
            child_religion = mother.religion
            child_gender_law = mother.gender_law
        else:
            if random.random() < 0.5:
                child_dynasty = father.dynasty
                child_is_house = father.is_house
                child_culture = father.culture
                child_religion = father.religion
                child_gender_law = father.gender_law
            else:
                child_dynasty = mother.dynasty
                child_is_house = mother.is_house
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
            is_house=child_is_house,            
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
        """Assigns a child's name based on dynasty inheritance chances."""
        
        # Fetch dynasty config
        dynasties = self.config.get('initialization', {}).get('dynasties', [])
        current_dynasty = next((dyn for dyn in dynasties if dyn['dynastyID'] == child_dynasty), None)

        if not current_dynasty:
            logging.warning(f"Dynasty {child_dynasty} not found. Assigning random name.")
            assigned_name = self.name_loader.load_names(mother.culture, child_sex.lower())
            return self.ensure_unique_name(assigned_name, mother, father, child_sex.lower())

        # Get name inheritance chances
        inheritance_chances = current_dynasty['nameInheritance']
        options = ['grandparent', 'parent', 'none']
        probabilities = [
            inheritance_chances['grandparentNameInheritanceChance'],
            inheritance_chances['parentNameInheritanceChance'],
            inheritance_chances['noNameInheritanceChance']
        ]
        
        chosen_method = random.choices(options, probabilities)[0]
        
        # Try to assign a grandparent's name
        if chosen_method == 'grandparent':
            assigned_name = None
            if child_sex == "Male":
                grandfather = father.father if father else None
                assigned_name = grandfather.name if grandfather else None
            elif child_sex == "Female":
                grandmother = mother.mother if mother else None
                assigned_name = grandmother.name if grandmother else None
            
            if assigned_name:
                return self.ensure_unique_name(assigned_name, mother, father, child_sex.lower())

        # Try to assign a parent's name
        if chosen_method == 'parent':
            assigned_name = father.name if child_sex == "Male" else mother.name
            return self.ensure_unique_name(assigned_name, mother, father, child_sex.lower())

        # Assign a random name from the name list
        assigned_name = self.name_loader.load_names(mother.culture, child_sex.lower())
        return self.ensure_unique_name(assigned_name, mother, father, child_sex.lower())

			
    def ensure_unique_name(self, proposed_name, mother, father, child_gender):
        """Ensures every child receives a name, even if it's a duplicate."""
        existing_names = {child.name for child in mother.children + father.children if child.alive}

        # Try to assign a unique random name
        unique_name = self.get_unique_random_name(mother.culture, child_gender, existing_names)
        if unique_name:
            logging.debug(f"Assigned unique random name: {unique_name}")
            return unique_name

        # If no unique names are available, assign a completely random name
        random_name = self.get_random_name(mother.culture, child_gender)
        logging.warning(f"No unique names available. Assigned random name: {random_name}")
        return random_name
				
    def get_unique_random_name(self, culture, child_sex, existing_names):
        """Returns a unique name if possible; otherwise, returns None."""
        available_names = self.name_loader.get_all_names(culture, child_sex)

        return random.choice(available_names) if available_names else None
    
    def get_random_name(self, culture, child_sex):
        """Returns a completely random name from the name list."""
        available_names = self.name_loader.get_all_names(culture, child_sex)
        
        if available_names:
            return random.choice(available_names)

        logging.error(f"No available names for culture '{culture}' and sex '{child_sex}'. Assigning fallback.")
        return f"Default_{child_sex}"  # Fallback name if list is empty


    def match_marriages(self, males, females, year):
        # Track dynasty sizes
        dynasty_sizes = {dyn: 0 for dyn in set(c.dynasty for c in self.all_characters if c.dynasty)}
        for character in self.all_characters:
            if character.alive:
                dynasty_sizes[character.dynasty] += 1

        # Prioritize dynasties with fewer members for marriage
        males.sort(key=lambda c: dynasty_sizes.get(c.dynasty, 0))
        females.sort(key=lambda c: dynasty_sizes.get(c.dynasty, 0))

        # Ensure all progenitor children get married
        for character in self.all_characters:
            if character.alive and not character.married and character.age >= 18:
                self.desperation_marriage_check(character, self.config['initialization']['minYear'] + 20)

        for male in males:
            if not male.alive or male.married or not male.can_marry:
                continue
            
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
            
            if self.desperation_marriage_check(male, year):
                continue
            
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
        child_is_house = parent.is_house       
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
            is_house=child_is_house,            
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
                        death_date = generate_random_date(year)
                        character.death_year, character.death_month, character.death_day = map(int, death_date.split('.'))
                        self.remove_from_unmarried_pools(character)
                        self.title_history.process_death(character)
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
        dynasty_groups = {}
        exported_character_count = 0

        for character in self.all_characters:
            if character.dynasty not in dynasty_groups:
                dynasty_groups[character.dynasty] = []
            dynasty_groups[character.dynasty].append(character)

        with open(output_filename, 'w', encoding='utf-8') as file:
            for dynasty, characters in sorted(dynasty_groups.items(), key=lambda x: x[0] or ""):
                file.write("################\n")
                file.write(f"### Dynasty {dynasty}\n")
                file.write("################\n\n")

                for character in sorted(characters, key=lambda c: c.birth_year):
                    file.write(character.format_for_export())
                    file.write("\n")  # Separate characters for readability
				
                    # Increment the counter after each character is written
                    exported_character_count += 1
				
        logging.info(f"Character history exported to {output_filename}")
        logging.info(f"Total characters exported: {exported_character_count}")
