import os
import random
import logging
import re

from ck3gen.character import Character
from utils.utils import generate_random_date, generate_char_id
from ck3gen.name_loader import NameLoader

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

        # Load dynasty‑level cousin‑marriage rule
        self.allow_cousin_marriage = {
            d['dynastyID']: d.get('allowFirstCousinMarriage', False)
            for d in config['initialization']['dynasties']
        }
        
        self.prioritise_lowborn_marriage = {
            d['dynastyID']: d.get('prioritiseLowbornMarriage', False)
            for d in config['initialization']['dynasties']
        }

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

    def get_num_fertile_dynasty_members(self, character):
        """Return list of alive and fertile characters from the same dynasty."""
        if not character.dynasty:
            return []

        def is_fertile(c):
            if not c.alive:
                return False
            age = c.age
            if c.sex == "Male":
                return 16 <= age <= 70
            elif c.sex == "Female":
                return 16 <= age <= 45
            return False

        return [
            c for c in self.all_characters
            if c.dynasty == character.dynasty and is_fertile(c)
        ]

    def desperation_marriage_check(self, character, year):
        # 1) never allow until age 16 + 5yrs per tier
        min_age = 16 + (character.numenorean_blood_tier or 0) * 5
        if character.age < min_age:
            return False

        # 2) pull the shifted rate
        desperation_chance = self.desperation_value(character)
        
        if random.random() < desperation_chance:
            self.generate_lowborn_and_marry(character, year)
            # print(f'{character.char_id} ({character.birth_year}) and {spouse.char_id} ({spouse.birth_year}) married in {year} desperately with desperation of {desperation_chance}')

    def desperation_value(self, character):
        """Check if an unmarried character is willing to marry a lowborn due to desperation."""
        age  = character.age
        tier = character.numenorean_blood_tier or 0
        # 2) compute “effective age” for the desperationRates lookup
        eff_age = age - tier * 5
        eff_age = max(eff_age, 0)
        last_idx = len(self.desperation_rates) - 1
        eff_age = min(eff_age, last_idx)
        base_chance = self.desperation_rates[eff_age]
            # Modify desperation based on dynasty size
        dynasty_members = self.get_num_fertile_dynasty_members(character)
        living_count = len(dynasty_members)
        num_dynasty_members_alive_modifier = (max(0,10 - living_count) * 0.20) + 1.0
        return min (1.0,  base_chance * num_dynasty_members_alive_modifier)

    def generate_lowborn_and_marry(self, character, year):
        logging.debug("Lowborn marriage happened, Char ID: %s", character.char_id)
        dynasty_prefix = character.dynasty.split('_')[1] if character.dynasty and '_' in character.dynasty else "lowborn"
        spouse_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)
        spouse_name = self.name_loader.load_names(character.culture, "male" if character.sex == "Female" else "female")
        if character.numenorean_blood_tier:
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
                birth_order=1,
                numenorean_blood_tier=character.numenorean_blood_tier
            )
        else:
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
            if birth_year >= event.get("startYear") and birth_year <= event.get("endYear") and age >= event.get("characterAgeStart") and age <= event.get("characterAgeEnd"):
                mortality_event_multipler = 1 - event.get("deathMultiplier")
                character.negativeEventDeathReason = event.get("deathReason")
                # print(f"Negative Char Event: {character.negativeEventDeathReason} | Current Age: {age}")
                # print(type(mortality_event_multipler))
                # print(f"Mortality Multipler: {mortality_event_multipler} | Current Birth Year: {birth_year} | Event Start Year: {event.get("startYear")} | Event End Year: {event.get("endYear")}")
        
        random_var = random.random()
        if self.prioritise_lowborn_marriage.get(character.dynasty, False):
            random_var *= 0.35
        
                
        return (random_var * mortality_event_multipler) < mortality_rate

    def marry_characters(self, char1, char2, year, marriage_type=None, children_dynasty=None):
        if char1.char_id == char2.char_id:
            logging.info(f"Attempted self-marriage for {char1.char_id}. Skipping.")
            return
        
        if (char1.married or char2.married):
            logging.debug(
                "One of the characters is already married: %s, %s. Skipping.",
                char1.char_id, char2.char_id,
            )
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
        char1.marriage_year = year
        char2.marriage_year = year

        # Remove from unmarried pools
        self.remove_from_unmarried_pools(char1)
        self.remove_from_unmarried_pools(char2)

        # Record marriage event
        marriage_date = generate_random_date(year)
        char1.add_event(marriage_date, f"{marriage_type} = {char2.char_id}")

    def has_dynasty(self, c: Character) -> bool:
        # True for any non-lowborn dynasty string.
        return c and c.dynasty and c.dynasty != "Lowborn"

    def sibling_index(self, c: Character) -> int:
        #0-based birth order among the children of the first parent found.
        p = c.father or c.mother
        if not p:
            return 0
        ordered = sorted(
            p.children,
            key=lambda x: (x.birth_year or 0, x.birth_month or 1, x.birth_day or 1)
        )
        try:
            return ordered.index(c)
        except ValueError:
            return len(ordered)

    def dyn_grandparent(self, child: Character) -> Character | None:
        # Return ONE of the grand-parents who shares the childs dynasty.
        # If both do, choose the senior (lower sibling index).

        gps = [gp for gp in (child.father, child.mother) if self.has_dynasty(gp)
            and gp.dynasty == child.dynasty]
        if not gps:
            return None
        if len(gps) == 1:
            return gps[0]
        return min(gps, key=self.sibling_index)

    def elder_of(self, a: Character, b: Character) -> Character: # Selects for eldest line
        # dynasty presence shortcut
        ad, bd = self.has_dynasty(a), self.has_dynasty(b)
        if ad and not bd:
            return a
        if bd and not ad:
            return b
        # (if neither has a dynasty, fall through – shouldn't occur per rules)

        # compare birth-order among siblings 
        ia, ib = self.sibling_index(a), self.sibling_index(b)
        if ia != ib:
            return a if ia < ib else b

        # tie → look one generation up on each side 
        gpa, gpb = self.dyn_grandparent(a), self.dyn_grandparent(b)

        # if only one side can climb, the other (root) side wins
        if gpa and not gpb:
            return a
        if gpb and not gpa:
            return b
        if not gpa and not gpb:
            return a  # both lines exhausted ⇒ deterministic pick

        # both grand-parents found – recurse
        return self.elder_of(gpa, gpb)

    def create_child(self, mother, father, birth_year) -> Character:

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

        # **Apply gender bias (+40%) only if no sibling of that gender exists**
        base_chance = 0.5
        if gender_preference == "Male" and not has_male_sibling:
            male_chance = 0.9
        elif gender_preference == "Female" and not has_female_sibling:
            male_chance = 0.1
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
            elder_parent = self.elder_of(mother, father)
            if elder_parent is father:
                child_dynasty   = father.dynasty
                child_is_house  = father.is_house
                child_culture   = father.culture
                child_religion  = father.religion
                child_gender_law = father.gender_law
            else:                                # mother is the elder line
                child_dynasty   = mother.dynasty
                child_is_house  = mother.is_house
                child_culture   = mother.culture
                child_religion  = mother.religion
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

        def is_fertile(c):
            if not c.alive:
                return False
            age = c.age
            if c.sex == "Male":
                return 16 <= age <= 70
            elif c.sex == "Female":
                return 16 <= age <= 45
            return False

        alive_members_in_dynasy = 0
        for character in self.all_characters:
            if character.dynasty == child_dynasty and character.alive and is_fertile(character):
                alive_members_in_dynasy += 1
                
        if alive_members_in_dynasy > 8:
            if child_sex == "Male":
                if father.fertilityModifier != 1:
                    fertilityModifier *= father.fertilityModifier
            else:
                if mother.fertilityModifier != 1:
                    fertilityModifier *= mother.fertilityModifier
        elif alive_members_in_dynasy <= 8:
            fertilityModifier = 1

        # Reduce fertility for dynasties configured to prioritise lowborn marriage.
        # Applied after the dynasty-size block so it is not overwritten by the reset to 1.
        if father.dynasty == child_dynasty and self.prioritise_lowborn_marriage.get(father.dynasty, False):
            fertilityModifier *= father.fertilityModifier * 0.65
        elif mother.dynasty == child_dynasty and self.prioritise_lowborn_marriage.get(mother.dynasty, False):
            fertilityModifier *= mother.fertilityModifier * 0.65

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
            return self.ensure_unique_name(mother, father, child_sex.lower())

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
            if child_sex == "Male":
                grandfather = father.father if father else None
                assigned_name = grandfather.name if grandfather else None
            else:
                grandmother = mother.mother if mother else None
                assigned_name = grandmother.name if grandmother else None
            
            # Return the grandparent name directly when one was found; otherwise fall through to random
            if assigned_name:
                return assigned_name

        # Try to assign a parent's name
        if chosen_method == 'parent':
            return father.name if child_sex == "Male" else mother.name

        # No inheritance — assign a random name from the culture pool
        return self.ensure_unique_name(mother, father, child_sex.lower())
	
    def ensure_unique_name(self, mother, father, child_gender):
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
            
            prioritise_lowborn = self.prioritise_lowborn_marriage.get(male.dynasty, False)
            try_lowborn_first = prioritise_lowborn and random.random() < 0.6
            
            if try_lowborn_first:
                self.generate_lowborn_and_marry(male, year)
                continue

            # Prioritize marriage for firstborn children
            available_females = [
                f for f in females
                if f.alive
                and not f.married
                and f.can_marry
                and (f.dynasty != male.dynasty or f.dynasty is None)
                and not self.are_siblings(male, f)
                and (
                    self.allow_cousin_marriage.get(male.dynasty, False)
                    or not self.are_first_cousins(male, f)
                )
                and abs(f.age - male.age) <= max(
                    self.max_age_diff_for(male),
                    self.max_age_diff_for(f)
                )
            ]
            
            if available_females:
                female = self.pick_partner_by_blood_preference(male, available_females)
                self.marry_characters(male, female, year)
                continue
            
            # If no match, try desperation marriage
            if self.desperation_marriage_check(male, year):
                continue

            # If still no match, prioritize same-dynasty marriage
            available_females = [
                f for f in females 
                if (
                    f.alive
                    and not f.married
                    and f.can_marry
                    and f.dynasty == male.dynasty
                    and not self.are_siblings(male, f)
                    # ◀ skip first‑cousins unless this dynasty allows it
                    and (
                        self.allow_cousin_marriage.get(male.dynasty, False)
                        or not self.are_first_cousins(male, f)
                    )
                    and abs(f.age - male.age) <= max(
                        self.max_age_diff_for(male),
                        self.max_age_diff_for(f)
                    )
                )
            ]
            
            if available_females:
                female = self.pick_partner_by_blood_preference(male, available_females)
                self.marry_characters(male, female, year)

    def are_siblings(self, char1, char2) -> Character:
        return char2 in char1.siblings()
    
    def are_first_cousins(self, char1, char2) -> bool:
        for p1 in (char1.father, char1.mother):
            for p2 in (char2.father, char2.mother):
                if p1 and p2 and self.are_siblings(p1, p2):
                    return True
        return False

    def pick_partner_by_blood_preference(self, seeker, candidates):
        """
        Return *one* candidate from candidates according to the rules:

        • blooded seeker  → prefer blooded partner, closest tier
        • non‑blood seeker → prefer non‑blood, else lowest tier blood
        """
        if not candidates:
            return None

        # current tiers (0 == no blood)
        t_seek = seeker.numenorean_blood_tier or 0
        if t_seek > 0:
            # --- blooded seeker ---------------------------------------
            blooded = [c for c in candidates if (c.numenorean_blood_tier or 0) > 0]
            if blooded:
                # minimise |tier diff|
                best_dist = min(abs(t_seek - (c.numenorean_blood_tier or 0)) for c in blooded)
                best = [c for c in blooded
                        if abs(t_seek - (c.numenorean_blood_tier or 0)) == best_dist]
                return random.choice(best)
            # else: nobody with blood → fall through to vanilla choice

        else:
            # --- non‑blood seeker -------------------------------------
            non_blood = [c for c in candidates if (c.numenorean_blood_tier or 0) == 0]
            if non_blood:
                return random.choice(non_blood)

            # no tier‑0 partner available → take the *lowest* tier present
            lowest = min(c.numenorean_blood_tier or 0 for c in candidates)
            best   = [c for c in candidates
                      if (c.numenorean_blood_tier or 0) == lowest]
            return random.choice(best)

        # default fall‑back (all rules exhausted)
        return random.choice(candidates)        

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
        child.assign_personality_traits(self.config['skills_and_traits']['personalityTraits'])

        # Record the childhood trait event at age 3
        skill = child.education_skill or "diplomacy"
        childhood_choices = self.childhood_by_education.get(skill, ["charming", "curious"])
        childhood_trait = random.choice(childhood_choices)
        childhood_date = f"{adjusted_birth_year + 3}.{child.birth_month:02d}.{child.birth_day:02d}"
        child.add_event(childhood_date, f"trait = {childhood_trait}")

        # Record the personality trait event at age 16
        trait_date = f"{adjusted_birth_year + 16}.{child.birth_month:02d}.{child.birth_day:02d}"
        detail_lines = [f"trait = {t}" for t in child.personality_traits]
        event_detail = "\n    ".join(detail_lines)
        child.add_event(trait_date, event_detail)

        return child

    # ------------------------------------------------------------------
    #  Refactored Simulation Loop
    # ------------------------------------------------------------------

    def _prepare_simulation_vars(self):
        """Caches frequently used config values as instance attributes."""
        life_stages = self.config['life_stages']
        self.desperation_rates = life_stages.get('desperationMarriageRates', [0.0]*121)
        self.marriage_rates = life_stages['marriageRates']
        self.fertility_rates = life_stages['fertilityRates']
        self.bastardy_chance_male = life_stages['bastardyChanceMale']
        self.bastardy_chance_female = life_stages['bastardyChanceFemale']
        self.maximum_children = life_stages['maximumNumberOfChildren']
        
        fer_f = self.fertility_rates['Female']
        fer_m = self.fertility_rates['Male']
        
        self.peak_f  = max(fer_f[16:]) if len(fer_f) > 16 else 0.0
        self.peak_m  = max(fer_m[16:]) if len(fer_m) > 16 else 0.0
        self.fer_f   = fer_f
        self.fer_m   = fer_m

    def _process_yearly_updates(self, year):
        """Updates ages and triggers age-based events for all characters."""
        for character in self.all_characters:
            character.negativeEventDeathReason = None # Reset flag
            if not character.alive:
                continue

            character.age = year - character.birth_year
            if character.age < 0:
                character.age = 0

            # Age 3: Childhood Trait
            if character.age == 3:
                skill = character.education_skill or "diplomacy"
                choices = self.childhood_by_education.get(skill, ["charming", "curious"])
                trait = random.choice(choices)
                date = f"{year}.{character.birth_month:02d}.{character.birth_day:02d}"
                character.add_event(date, f"trait = {trait}")

            # Age 16: Personality Traits
            # Guard prevents re-assignment for characters who received traits at creation (e.g. bastards)
            if character.age == 16 and not character.personality_traits:
                character.assign_personality_traits(self.config['skills_and_traits']['personalityTraits'])
                date = f"{year}.{character.birth_month:02d}.{character.birth_day:02d}"
                detail_lines = [f"trait = {t}" for t in character.personality_traits]
                event_detail = "\n    ".join(detail_lines)
                character.add_event(date, event_detail)

    def _process_marriages(self, year):
        """Clears and updates marriage pools, then matches couples."""
        self.unmarried_males.clear()
        self.unmarried_females.clear()
        
        self.update_unmarried_pools(year)

        # Extract all unmarried males and females from the populated pools
        all_unmarried_males = [m for males in self.unmarried_males.values() for m in males]
        all_unmarried_females = [f for females in self.unmarried_females.values() for f in females]

        if all_unmarried_males and all_unmarried_females:
            self.match_marriages(all_unmarried_males, all_unmarried_females, year)

    def _process_births(self, year):
        """Handles births from married couples and bastardy."""
        # 1. Handle married births
        for character in self.all_characters:
            if not (character.alive and character.married and character.sex == "Female"):
                continue
            
            # Check if character has reached maximum number of children
            if len(character.children) >= self.maximum_children:
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
            total_fertility = fertility_rate * fertility_rate_m
            
            if random.random() < total_fertility:
                child = self.create_child(character, character.spouse, year)
                if child:
                    self.add_character_to_pool(child)
                    self.all_characters.append(child)
        
        # 2. Handle Bastardy
        self.handle_bastardy(year, self.bastardy_chance_male, self.bastardy_chance_female, self.fertility_rates)

    def _process_deaths(self, year):
        """Checks for and processes character deaths."""
        for character in self.all_characters:
            if not character.alive:
                continue
            
            if self.character_death_check(character):
                character.alive = False
                character.death_year = year
                death_date = generate_random_date(year)
                character.death_year, character.death_month, character.death_day = map(int, death_date.split('.'))
                self.remove_from_unmarried_pools(character)
                
                # Determine death cause
                if character.negativeEventDeathReason is not None:
                    death_cause = character.negativeEventDeathReason
                elif character.age > (65 + (20 * (character.numenorean_blood_tier or 0))):
                    death_cause = "death_natural_causes"
                elif character.age < 18:
                    death_cause = "death_ill"
                elif character.sex == "Male":
                    death_cause = random.choice([
                        "death_ill", "death_cancer", "death_battle", "death_attacked",
                        "death_accident", "death_murder", "death_natural_causes",
                        "death_drinking_passive", "death_dungeon_passive"
                    ])
                else:
                    death_cause = random.choice([
                        "death_ill", "death_cancer", "death_accident", "death_murder"
                    ])
                    
                character.add_event(death_date, f"death = {{ death_reason = {death_cause} }}")
                
                if character.married and character.spouse.alive:
                    character.spouse.married = False
                    character.spouse.married = None # Matches original file logic

    def _process_survivor_deaths(self, last_sim_year):
        """
        Estimates death dates for all characters who survived the simulation.
        This runs a simplified "post-simulation" loop.
        """
        survivors = [c for c in self.all_characters if c.alive]
        if not survivors:
            return

        logging.info(f"Estimating death dates for {len(survivors)} survivors...")
        
        year = last_sim_year
        while survivors:
            year += 1
            # Iterate backwards to safely remove items
            for i in range(len(survivors) - 1, -1, -1):
                character = survivors[i]
                
                # Update age for this year
                character.age = year - character.birth_year
                
                # Reset event-based death reason, as sim events are over
                character.negativeEventDeathReason = None

                # Run the exact same death check
                if self.character_death_check(character):
                    character.alive = False  # Mark as "processed"
                    character.death_year = year
                    death_date = generate_random_date(year)
                    character.death_year, character.death_month, character.death_day = map(int, death_date.split('.'))
                    
                    # --- Copied death cause logic from _process_deaths ---
                    # Use negativeEventDeathReason if set by the (weird) check
                    if character.negativeEventDeathReason is not None:
                        death_cause = character.negativeEventDeathReason
                    # Otherwise, use the standard age-based causes
                    elif character.age > (65 + (20 * (character.numenorean_blood_tier or 0))):
                        death_cause = "death_natural_causes"
                    elif character.age < 18:
                        death_cause = "death_ill"
                    elif character.sex == "Male":
                        death_cause = random.choice([
                            "death_ill", "death_cancer", "death_battle", "death_attacked",
                            "death_accident", "death_murder", "death_natural_causes",
                            "death_drinking_passive", "death_dungeon_passive"
                        ])
                    else:
                        death_cause = random.choice([
                            "death_ill", "death_cancer", "death_accident", "death_murder"
                        ])
                    # --- End of copied logic ---
                        
                    character.add_event(death_date, f"death = {{ death_reason = {death_cause} }}")
                    
                    # Remove from survivor list
                    survivors.pop(i)

    def run_simulation(self):
        """
        Runs the main simulation loop, processing events year by year.
        """
        self._prepare_simulation_vars()

        min_year = self.config['initialization']['minYear']
        max_year = self.config['initialization']['maxYear']

        for year in range(min_year, max_year + 1):
            
            # 1. Update ages and apply age-based traits (3 & 16)
            self._process_yearly_updates(year)
						
            # 2. Handle Marriages
            self._process_marriages(year)

            # 3. Handle Births (Married & Bastardy)
            self._process_births(year)

            # 4. Check for Deaths
            self._process_deaths(year)

            # 5. Update Unmarried Pools
            # This is to catch anyone who became eligible *after* death/etc.
            self.update_unmarried_pools(year) 
            
        # Process survivors
        logging.info("Main simulation loop complete. Processing survivors...")
        self._process_survivor_deaths(max_year)

    def export_characters(self, output_filename="family_history.txt"):
        from ck3gen.paths import CHARACTER_OUTPUT_DIR
        CHARACTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = CHARACTER_OUTPUT_DIR / output_filename

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