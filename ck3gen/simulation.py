import os
import random
import logging
import re
from ck3gen.character import Character
from utils.utils import generate_random_date, generate_char_id
from ck3gen.name_loader import NameLoader
from ck3gen.title_history import TitleHistory

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
        self.desperation_rates = self.config['life_stages'].get('desperationMarriageRates', {})
        self.marriage_min_age = 16
        self.numenor_marriage_inc = 5
        self.marriage_rates    = config['life_stages']['marriageRates']
        self.desperation_rates = config['life_stages']['desperationMarriageRates']

        # Map each education skill to its two possible childhood traits
        self.childhood_by_education = {
            "diplomacy":    ["charming", "curious"],
            "intrigue":     ["charming", "rowdy"],
            "martial":      ["rowdy",   "bossy"],
            "stewardship":  ["pensive", "bossy"],
            "learning":     ["pensive", "curious"],
        }

    def add_character_to_pool(self, character):
        """ Adjust fertility and mortality based on dynasty rules """
        mortality_penalty = character.apply_dynasty_mortality_penalty()

        # Modify fertility rates dynamically
        base_fertility = self.config['life_stages']['fertilityRates']['Female']
        self.config['life_stages']['fertilityRates']['Female'] = base_fertility

        # Apply mortality penalty (pseudo-code, assuming there's a mortality function)
        character.mortality_risk += mortality_penalty  

        # Add to character pool
        self.character_pool.setdefault(character.birth_year, []).append(character)

    def remove_from_unmarried_pools(self, character):
        age = character.age
        pool = self.unmarried_males if character.sex == 'Male' else self.unmarried_females
        if age in pool and character in pool[age]:
            pool[age].remove(character)

    def update_unmarried_pools(self, year):
        for char in self.all_characters:
            if not (char.alive and not char.married and char.can_marry):
                continue

            age  = char.age
            tier = char.numenorean_blood_tier or 0

            # 1) enforce absolute minimum (16 + 5×tier)
            if age < self.marriage_min_age + tier*self.numenor_marriage_inc:
                continue

            # 2) compute “effective age” for your lookup
            eff_age = age - tier*self.numenor_marriage_inc
            eff_age = max(eff_age, 0)
            max_idx = len(self.marriage_rates[char.sex]) - 1
            eff_age = min(eff_age, max_idx)

            rate = self.marriage_rates[char.sex][eff_age]
            if rate > 0 and random.random() < rate:
                pool = self.unmarried_males if char.sex=="Male" else self.unmarried_females
                pool.setdefault(age, []).append(char)

    def get_extended_fertility_rate(self, char, sex):
        base = self.fer_f if sex == 'Female' else self.fer_m
        peak = self.peak_f if sex == 'Female' else self.peak_m

        age  = char.age
        tier = char.numenorean_blood_tier or 0
        extra = 10 * tier
        n     = len(base)

        # 1) before 16 → just use the table if available
        if age < 16:
            return base[age] if age < n else 0.0

        # 2) plateau at peak for the extra‑years window
        if age <= 16 + extra:
            return peak

        # 3) shift the lookup and clamp into [0..n-1]
        eff = age - extra
        if eff < 0:
            eff = 0
        elif eff >= n:
            eff = n - 1

        rate = base[eff]

        # 4) apply the –2.5% per tier penalty
        penalty = max(0.0, 1.0 - tier * 0.025)
        return rate * penalty

    def max_age_diff_for(self, character):
        """
        Return the maximum allowed age difference for a given character,
        as base + (blood tier × hard‑coded increment).
        """
        tier = character.numenorean_blood_tier or 0
        return self.marriage_max_age_diff + tier * 5

    def desperation_marriage_check(self, character, year):
        """Check if an unmarried character is willing to marry a lowborn due to desperation."""
        age  = character.age
        tier = character.numenorean_blood_tier or 0

        # 1) never allow until age 16 + 5yrs per tier
        min_age = 16 + tier * 5
        if age < min_age:
            return False

        # 2) compute “effective age” for the desperationRates lookup
        eff_age = age - tier * 5
        eff_age = max(eff_age, 0)
        last_idx = len(self.desperation_rates) - 1
        eff_age = min(eff_age, last_idx)

        # 3) pull the shifted rate
        desperation_chance = self.desperation_rates[eff_age]
        
        if random.random() < desperation_chance:
            # Generate a lowborn spouse
            dynasty_prefix = character.dynasty.split('_')[1] if character.dynasty and '_' in character.dynasty else "lowborn"
            spouse_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)
            spouse_name = self.name_loader.load_names(character.culture, "male" if character.sex == "Female" else "female")
            
            # Ensure lowborn is human and fertile
            spouse = Character(
                char_id=spouse_char_id,
                name=spouse_name,
                sex="Male" if character.sex == "Female" else "Female",
                birth_year=year-random.randint(18, 26),
                dynasty=None,  # Lowborns do not have a dynasty
                is_house=False,
                culture=character.culture,
                religion=character.religion,
                gender_law=character.gender_law,
                sexuality_distribution=self.config['skills_and_traits']['sexualityDistribution'],
                generation=character.generation,
                is_progenitor=False,
                birth_order=1
            )
            if spouse:
                self.add_character_to_pool(spouse)
                self.all_characters.append(spouse)
                spouse.assign_skills(self.config['skills_and_traits']['skillProbabilities'])
                spouse.assign_education(self.config['skills_and_traits']['educationProbabilities'])
                spouse.assign_personality_traits(self.config['skills_and_traits']['personalityTraits'])
                # pick from the two that correspond to their education_skill
                skill = spouse.education_skill or "diplomacy"
                choices = self.childhood_by_education.get(skill, ["charming","curious"])
                trait = random.choice(choices)
                date = f"{spouse.birth_year+3}.{spouse.birth_month:02d}.{spouse.birth_day:02d}"
                spouse.add_event(date, f"trait = {trait}")
                # build the date (their real birthday)
                date = f"{spouse.birth_year+16}.{spouse.birth_month:02d}.{spouse.birth_day:02d}"
                # collect the three personality traits…
                detail_lines = [f"trait = {t}" for t in spouse.personality_traits]
                # join them into one block (each on its own line, indented by 4 spaces)
                event_detail = "\n    ".join(detail_lines)
                # emit a single event with all four lines
                spouse.add_event(date, event_detail)

            spouse_dynasty = character.dynasty  # Noble's dynasty does not transfer
            self.marry_characters(character, spouse, year, children_dynasty=spouse_dynasty)
            # print(f'{character.char_id} ({character.birth_year}) and {spouse.char_id} ({spouse.birth_year}) married in {year} desperately with desperation of {desperation_chance}')

    def character_death_check(self, character):
        age = character.age
        # effective age for mortality = real age minus 20yrs per blood tier
        tier = character.numenorean_blood_tier or 0
        age = character.age - 20 * tier
        if age < 0:
            age = 0

        sex = character.sex
        birth_year = character.birth_year  # Assuming character has a birth year attribute
        mortality_event_multipler = 1

        # If the character is a progenitor, ensure they live until at least age 50
        if character.is_progenitor and age < 50:
            return 0  # Set age to 50 for progenitors, ensuring they live this long

        if age < 0 or age > 120:
            age = max(0, min(age, 120))

        mortality_rates = self.config['life_stages']['mortalityRates'][sex]

        if age < 1:
            mortality_rate = 0  # Ensure no deaths before age 1
        elif age < len(mortality_rates):
            mortality_rate = mortality_rates[age]
        else:
            mortality_rate = 1.0  # 100% chance of death

        for event in self.config.get('initialization', {}).get('events', []):
            if birth_year > event.get("startYear") and birth_year < event.get("endYear") and age >= event.get("characterAgeStart") and age <= event.get("characterAgeEnd"):
                mortality_event_multipler = event.get("deathMultiplier")
                character.negativeEventDeathReason = event.get("deathReason")
                # print(f"Negative Char Event: {character.negativeEventDeathReason} | Current Age: {age}")
                # print(type(mortality_event_multipler))
                # print(f"Mortality Multipler: {mortality_event_multipler} | Current Birth Year: {birth_year} | Event Start Year: {event.get("startYear")} | Event End Year: {event.get("endYear")}")
        random_var = random.random()
                
        return (random_var * mortality_event_multipler) < mortality_rate

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
            if (char1.gender_law == "AGNATIC" or char1.gender_law == "AGNATIC_COGNATIC") and char1.sex == "Male":
                marriage_type = "add_spouse"
                children_dynasty = char1.dynasty
            elif (char1.gender_law == "ENATIC" or char1.gender_law == "ENATIC_COGNATIC") and char1.sex == "Female":
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

        #print(f"Father Age:",{father.age},"Father Fertility:",{self.config['life_stages']['fertilityRates']['Female'][father.age]},"Mother Age:",{mother.age},"Mother Fertility:",{self.config['life_stages']['fertilityRates']['Female'][mother.age]})

        # Enforce maximum number of children per woman
        maximum_children = self.config['life_stages']['maximumNumberOfChildren']
        if len(mother.children) >= maximum_children:
            return None

        # Enforce minimum years between children
        couple_key = (father.char_id, mother.char_id)
        last_birth_year = self.couple_last_child_year.get(couple_key, None)
        min_years = self.config['life_stages']['minimumYearsBetweenChildren']

        if last_birth_year is not None and birth_year < (last_birth_year + min_years):
            return None

        # Use fertilityRates to determine if a child is produced
        female_age = mother.age
        fertility_rate = self.config['life_stages']['fertilityRates']['Female'][female_age]
        
        # Proceed with child creation
        self.character_count += 1

        child_generation = max(mother.generation, father.generation) + 1

        if child_generation > self.config['initialization']['generationMax']:
            return None  # Do not create child

        # **Determine Gender Preference Based on Laws**
        gender_preference = None
        if father.gender_law == "AGNATIC" or father.gender_law == "AGNATIC_COGNATIC":
            gender_preference = "Male"
        elif mother.gender_law == "ENATIC" or mother.gender_law == "ENATIC_COGNATIC":
            gender_preference = "Female"

        # **Check existing siblings**
        siblings = mother.children + father.children  # Combine both parents' children
        has_male_sibling = any(sibling.sex == "Male" for sibling in siblings)
        has_female_sibling = any(sibling.sex == "Female" for sibling in siblings)

        # **Apply gender bias (+25%) only if no sibling of that gender exists**
        base_chance = 0.5
        if gender_preference == "Male" and not has_male_sibling:
            male_chance = 0.65
        elif gender_preference == "Female" and not has_female_sibling:
            male_chance = 0.35
        else:
            male_chance = base_chance  # No modification

        child_sex = "Male" if random.random() < male_chance else "Female"

        # Determine dynasty and culture based on marriage laws and parents
        if (mother.gender_law == "AGNATIC" or mother.gender_law == "AGNATIC_COGNATIC") and (father.gender_law == "AGNATIC" or father.gender_law == "AGNATIC_COGNATIC"):
            child_dynasty = father.dynasty
            child_is_house = father.is_house
            child_culture = father.culture
            child_religion = father.religion
            child_gender_law = father.gender_law
        elif (mother.gender_law == "ENATIC" or mother.gender_law == "ENATIC_COGNATIC") and mother.sex == "Female":
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

        # Assign birth order before creating the child
        birth_order = len(mother.children) + 1  # Calculate birth order based on mother's children
        fertilityModifier = 1
        if birth_order == 1:
            fertilityModifier = 1
        elif birth_order == 2:
            fertilityModifier = 0.80
        elif birth_order == 3:
            fertilityModifier = 0.60
        elif birth_order == 4:
            fertilityModifier = 0.40
        elif birth_order == 5:
            fertilityModifier = 0.20
        else:
            fertilityModifier = 0.10

        alive_members_in_dynasy = 0
        for character in self.all_characters:
            if character.dynasty == child_dynasty and character.alive:
                alive_members_in_dynasy += 1

        if alive_members_in_dynasy >= 15: #A lot of dynasty members are alive
            if child_sex == "Male":
                if father.fertilityModifier != 1:
                    fertilityModifier *= father.fertilityModifier
            else:
                if mother.fertilityModifier != 1:
                    fertilityModifier *= mother.fertilityModifier
        elif alive_members_in_dynasy < 10: #A low number of dynasty members are alive
            fertilityModifier = 1

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
            generation=child_generation,
            birth_order=birth_order,  # Pass birth order when creating the child
            fertilityModifier = fertilityModifier
        )

        # Assign Numenorean Blood
        inherit_params = (
            self.config
                .get("initialization", {})
                .get("numenorInheritance", {})
        )
        decline_table = (
            self.config
                .get("initialization", {})
                .get("numenorDecline", {})
        )
        Character.inherit_numenorean_blood(child, father, mother, inherit_params, decline_table)

        # Set parents
        child.father = father if father.sex == 'Male' else mother
        child.mother = mother if mother.sex == 'Female' else father

        # Add child to parents' children
        mother.children.append(child)
        father.children.append(child)

        # Assign skills, education, and personality traits
        child.assign_skills(self.config['skills_and_traits']['skillProbabilities'])
        child.assign_education(self.config['skills_and_traits']['educationProbabilities'])

        # Evaluate congenital traits
        Character.inherit_congenital(child, father, mother)

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
        males.sort(key=lambda c: (dynasty_sizes.get(c.dynasty, 0), c.birth_order if c.birth_order is not None else float('inf')))
        females.sort(key=lambda c: (dynasty_sizes.get(c.dynasty, 0), c.birth_order if c.birth_order is not None else float('inf')))

        for male in males:
            if not male.alive or male.married or not male.can_marry:
                continue
            
            # Prioritize marriage for firstborn children
            available_females = [
                f for f in females 
                if f.alive and not f.married and f.can_marry and 
                (f.dynasty != male.dynasty or f.dynasty is None) and 
                not self.are_siblings(male, f) and
                abs(f.age - male.age) <= max(
                    self.max_age_diff_for(male),
                    self.max_age_diff_for(f)
                )
            ]
            
            if available_females:
                female = random.choice(available_females)
                self.marry_characters(male, female, year)
                continue
            
            # If no match, try desperation marriage
            if self.desperation_marriage_check(male, year):
                continue

            # If still no match, prioritize same-dynasty marriage
            available_females = [
                f for f in females 
                if f.alive and not f.married and f.can_marry and 
                (f.dynasty == male.dynasty) and 
                not self.are_siblings(male, f) and
                abs(f.age - male.age) <= max(
                    self.max_age_diff_for(male),
                    self.max_age_diff_for(f)
                )
            ]
            
            if available_females:
                female = random.choice(available_females)
                self.marry_characters(male, female, year)

    def are_siblings(self, char1, char2):
        """Check if two characters are siblings based on shared parents."""
        return (char1.father is not None and char1.father == char2.father) and \
               (char1.mother is not None and char1.mother == char2.mother)
			   
    def handle_bastardy(self, year, bastardy_chance_male, bastardy_chance_female, fertility_rates):
        father_bastard_done = set() # track father IDs who have fathered a bastard this year
        
        for character in self.all_characters:
            if not character.alive or not character.dynasty or character.dynasty == "Lowborn":
                continue

            if character.sex == "Female":
                # Check if fertility rate is non-zero
                female_age = character.age
                fertility_rate = (
                    self.get_extended_fertility_rate(character, 'Female')
                    * character.fertility_mult()
                )
                
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
                # If father already fathered a bastard this year, skip
                if character.char_id in father_bastard_done:
                    continue

                # Apply bastardy chance
                if random.random() < bastardy_chance_male:
                    # Male has a bastard child
                    child = self.create_bastard_child(character, year, is_male=True)
                    if child:
                        self.add_character_to_pool(child)
                        self.all_characters.append(child)
                        father_bastard_done.add(character.char_id)

    def create_bastard_child(self, parent, birth_year, is_male):
        maximum_children = self.config['life_stages']['maximumNumberOfChildren']
        # Check if parent has reached maximum number of children
        if len(parent.children) >= maximum_children:
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

        # Determine Gender Preference Based on Laws
        gender_preference = None
        if parent.gender_law == "AGNATIC" or parent.gender_law == "AGNATIC_COGNATIC":
            gender_preference = "Male"
        elif parent.gender_law == "ENATIC" or parent.gender_law == "ENATIC_COGNATIC":
            gender_preference = "Female"

        # **Check existing siblings**
        siblings = parent.children  # Parent's children
        has_male_sibling = any(sibling.sex == "Male" for sibling in siblings)
        has_female_sibling = any(sibling.sex == "Female" for sibling in siblings)

        # Apply gender bias (+25%) only if no sibling of that gender exists
        base_chance = 0.5
        if gender_preference == "Male" and not has_male_sibling:
            male_chance = 0.65
        elif gender_preference == "Female" and not has_female_sibling:
            male_chance = 0.35
        else:
            male_chance = base_chance  # No modification

        child_sex = "Male" if random.random() < male_chance else "Female"

        # Assign dynasty and culture based on parent
        child_dynasty = parent.dynasty
        child_is_house = parent.is_house       
        child_culture = parent.culture
        child_religion = parent.religion
        child_gender_law = parent.gender_law

        # Handle lowborn characters (dynasty can be None)
        dynasty_prefix = child_dynasty.split('_')[1] if child_dynasty and '_' in child_dynasty else "lowborn"

        child_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)

        # Assign name based on inheritance chances
        child_name = self.assign_child_name(
            child_sex=child_sex,
            mother=parent,
            father=parent,
            child_dynasty=child_dynasty
        )

        sexuality_distribution = self.config['skills_and_traits']['sexualityDistribution']

        # Assign birth order before creating the child
        birth_order = len(parent.children) + 1  # Calculate birth order based on parent's children

        adjusted_birth_year = max(birth_year, parent.birth_year + 16)  # Adjust birth year based on parent's age
        child = Character(
            char_id=child_char_id,
            name=child_name,
            sex=child_sex,
            birth_year=adjusted_birth_year,
            dynasty=child_dynasty,
            is_house=child_is_house,            
            culture=child_culture,
            religion=child_religion,
            gender_law=child_gender_law,
            sexuality_distribution=sexuality_distribution,
            generation=child_generation,
            is_bastard=True,
            birth_order=birth_order  # Pass birth order when creating the child
        )

        # Set parent(s)
        if is_male:
            child.father = parent
            child.mother = None
            parent.children.append(child)
        else:
            child.mother = parent
            child.father = None
            parent.children.append(child)

        # Assign Numenorean Blood
        # inherit_params = self.config.get("numenorInheritance", {})
        inherit_params = (
            self.config
                .get("initialization", {})
                .get("numenorInheritance", {})
        )
        decline_table = (
            self.config
                .get("initialization", {})
                .get("numenorDecline", {})
        )
        Character.inherit_numenorean_blood(child, child.father, child.mother, inherit_params, decline_table)

        # Assign the 'bastard' trait
        child.add_trait('bastard')

        # Assign skills, education, and personality traits
        child.assign_skills(self.config['skills_and_traits']['skillProbabilities'])
        child.assign_education(self.config['skills_and_traits']['educationProbabilities'])
        # child.assign_personality_traits(self.config['skills_and_traits']['personalityTraits'])

        return child

    def run_simulation(self):
        life_stages = self.config['life_stages']
        self.desperation_rates = life_stages.get('desperationMarriageRates', [0.0]*121)
        marriage_rates = life_stages['marriageRates']
        fertility_rates = life_stages['fertilityRates']
        bastardy_chance_male = life_stages['bastardyChanceMale']
        bastardy_chance_female = life_stages['bastardyChanceFemale']
        maximum_children = life_stages['maximumNumberOfChildren']
        fer_f = life_stages['fertilityRates']['Female']
        fer_m = life_stages['fertilityRates']['Male']
        # Precompute once:
        self.peak_f  = max(fer_f[16:]) if len(fer_f) > 16 else 0.0
        self.peak_m  = max(fer_m[16:]) if len(fer_m) > 16 else 0.0
        self.fer_f   = fer_f
        self.fer_m   = fer_m

        for year in range(self.config['initialization']['minYear'], self.config['initialization']['maxYear'] + 1):
            # 0. Ensure we're not hanging on to old negative event death reasons
            for character in self.all_characters:
                character.negativeEventDeathReason = None
            
            # 1. Update Characters' Ages
            for character in self.all_characters:
                if character.alive:
                    character.age = year - character.birth_year
                    if character.age < 0:
                        character.age = 0

            # Give under‑bookmark kids their single childhood trait at age 3
            for character in self.all_characters:
                if character.alive and character.age == 3:
                    # pick from the two that correspond to their education_skill
                    skill = character.education_skill or "diplomacy"
                    choices = self.childhood_by_education.get(skill, ["charming","curious"])
                    trait = random.choice(choices)
                    # print(skill,choices,trait)
                    date = f"{year}.{character.birth_month:02d}.{character.birth_day:02d}"
                    character.add_event(date, f"trait = {trait}")

            # At age 16, under‑bookmark kids get *one* multi‑trait event
            for character in self.all_characters:
                if not (character.alive and character.age == 16):
                    continue

                # first pick their three adult traits
                character.assign_personality_traits(self.config['skills_and_traits']['personalityTraits'])

                # build the date (their real birthday)
                date = f"{year}.{character.birth_month:02d}.{character.birth_day:02d}"

                # collect the three personality traits…
                detail_lines = [f"trait = {t}" for t in character.personality_traits]

                # join them into one block (each on its own line, indented by 4 spaces)
                event_detail = "\n    ".join(detail_lines)

                # emit a single event with all four lines
                character.add_event(date, event_detail)
						
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
                    fertility_rate = (
                        self.get_extended_fertility_rate(character, 'Female')
                        * character.fertility_mult()
                    )
                    fertility_rate_m = (
                        self.get_extended_fertility_rate(character.spouse, 'Male')
                        * character.spouse.fertility_mult()
                    )
                    #     print(f"Male Fertility: {fertility_rate_m} | Male Fertility Modifier: {character.spouse.fertilityModifier} | Male Fertility Modified: {fertility_rate_m_modified} | Character: {character.spouse.char_id}")
                    total_fertility = fertility_rate * fertility_rate_m
                    if random.random() < total_fertility:
                        # print(f"Father Age: {male_age} "
                        # f"Father Fertility: {fertility_rate_m} "
                        # f"Mother Age: {female_age} "
                        # f"Mother Fertility: {fertility_rate}")
                        child = self.create_child(character, character.spouse, year)
                        if child:
                            self.add_character_to_pool(child)
                            self.all_characters.append(child)
							
            # 4. Handle Bastardy
            self.handle_bastardy(year, bastardy_chance_male, bastardy_chance_female, fertility_rates)

            # 5. Assign Skills, Education, and Traits at Age 16
            # for character in self.all_characters:
            #     if character.alive and character.age == 16:
            #         character.assign_skills(self.config['skills_and_traits']['skillProbabilities'])
            #         character.assign_education(self.config['skills_and_traits']['educationProbabilities'])
            #         character.assign_personality_traits(self.config['skills_and_traits']['personalityTraits'])

            # 6. Check for Deaths
            for character in self.all_characters:
                if character.alive:
                    if self.character_death_check(character):
                        character.alive = False
                        character.death_year = year
                        death_date = generate_random_date(year)
                        character.death_year, character.death_month, character.death_day = map(int, death_date.split('.'))
                        self.remove_from_unmarried_pools(character)
                        if character.negativeEventDeathReason != None:
                            death_cause = character.negativeEventDeathReason
                        elif character.age > (65+(20*(character.numenorean_blood_tier or 0))):
                            death_cause = "death_natural_causes"
                        elif character.age < 18:
                            death_cause = "death_ill"
                        elif character.sex == "Male":
                            death_cause = random.choice([
                                "death_ill",
                                "death_cancer",
                                "death_battle",
                                "death_attacked",
                                "death_accident", 
                                "death_murder", 
                                "death_natural_causes", 
                                "death_drinking_passive", 
                                "death_dungeon_passive"
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

        # for character in self.all_characters:
        #     if character.alive:
        #         character.age = year - character.birth_year
        #         if character.age < 0:
        #             character.age = 0
        #     # **Clear unmarried pools after updating ages**
        #     self.unmarried_males.clear()
        #     self.unmarried_females.clear()

        #     # 2. Handle Marriages
        #     # First, update unmarried pools based on marriage rates
        #     self.update_unmarried_pools(year)

        #     # Extract all unmarried males and females
        #     all_unmarried_males = []
        #     for age, males in self.unmarried_males.items():
        #         all_unmarried_males.extend(males)
        #     all_unmarried_females = []
        #     for age, females in self.unmarried_females.items():
        #         all_unmarried_females.extend(females)

        #     # Proceed to match marriages
        #     if all_unmarried_males and all_unmarried_females:
        #         self.match_marriages(all_unmarried_males, all_unmarried_females, year)

        #     # 5. Assign Skills, Education, and Traits at Age 16
        #     for character in self.all_characters:
        #         if character.alive and character.age == 16:
        #             character.assign_skills(self.config['skills_and_traits']['skillProbabilities'])
        #             character.assign_education(self.config['skills_and_traits']['educationProbabilities'])
        #             character.assign_personality_traits(self.config['skills_and_traits']['personalityTraits'])
                    
        #     # 6. Check for Deaths
        #     for character in self.all_characters:
        #         if character.alive:
        #             if self.character_death_check(character):
        #                 character.alive = False
        #                 character.death_year = year
        #                 death_date = generate_random_date(year)
        #                 character.death_year, character.death_month, character.death_day = map(int, death_date.split('.'))
        #                 self.remove_from_unmarried_pools(character)
        #                 if character.negativeEventDeathReason != None:
        #                     death_cause = character.negativeEventDeathReason
        #                 elif character.age > 65:
        #                     death_cause = "death_natural_causes"
        #                 elif character.age < 18:
        #                     death_cause = "death_ill"
        #                 elif character.sex == "Male":
        #                     death_cause = random.choice([
        #                         "death_ill",
        #                         "death_cancer",
        #                         "death_battle",
        #                         "death_attacked",
        #                         "death_accident", 
        #                         "death_murder", 
        #                         "death_natural_causes", 
        #                         "death_drinking_passive", 
        #                         "death_dungeon_passive", 
        #                         "death_giant"
        #                     ])
        #                 else:
        #                     death_cause = random.choice([
        #                         "death_ill",
        #                         "death_cancer",
        #                         "death_accident", 
        #                         "death_murder"
        #                     ])							
        #                 character.add_event(death_date, f"death = {{ death_reason = {death_cause} }}")
        #                 if character.married and character.spouse.alive:
        #                     character.spouse.married = False
        #                     character.spouse.married = None

        #     # 7. Update Unmarried Pools
        #     self.update_unmarried_pools(year)

    def export_characters(self, output_filename="family_history.txt"):
        # Set output folder and ensure it exists
        output_folder = "Character and Title files"
        os.makedirs(output_folder, exist_ok=True)

        # Full path to the output file
        output_path = os.path.join(output_folder, output_filename)

        dynasty_groups = {}
        exported_character_count = 0

        for character in self.all_characters:
            if character.dynasty:  # Only group characters with a valid dynasty
                if character.spouse and character.dynasty == "Lowborn":
                    dynasty = character.spouse.dynasty if character.spouse.dynasty != "Lowborn" else character.dynasty
                else:
                    dynasty = character.dynasty

                if dynasty not in dynasty_groups:
                    dynasty_groups[dynasty] = []
                dynasty_groups[dynasty].append(character)

        with open(output_path, 'w', encoding='utf-8') as file:
            for dynasty, characters in sorted(dynasty_groups.items(), key=lambda x: x[0]):
                file.write("################\n")
                file.write(f"### Dynasty {dynasty}\n")
                file.write("################\n\n")

                for character in sorted(characters, key=lambda c: int(re.sub(r'\D', '', c.char_id))):
                    file.write(character.format_for_export())
                    file.write("\n")
                    exported_character_count += 1

        logging.info(f"Character history exported to {output_path}")
        logging.info(f"Total characters exported: {exported_character_count}")



