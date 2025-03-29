import random
import logging
from utils import generate_random_date

class Character:
    def __init__(
        self, 
        char_id, 
        name, 
        sex, 
        birth_year, 
        dynasty, 
        culture, 
        religion, 
        gender_law, 
        sexuality_distribution, 
        is_house=False,
        generation=1, 
        is_progenitor=False,
        is_bastard=False
    ):
        self.is_bastard=False
        self.char_id = char_id
        self.name = name
        self.sex = sex
        self.birth_year = birth_year
        self.birth_month = 1  # Default month
        self.birth_day = 1    # Default day
        self.age = 0  # Will be updated annually
        self.death_year = None
        self.death_month = None
        self.death_day = None
        self.alive = True
        self.married = False
        self.spouse = None
        self.children = []
        self.dynasty = dynasty if dynasty else "Lowborn"
        self.gender_law = gender_law if gender_law in ["male", "female", "equal"] else "equal"
        self.culture = culture
        self.religion = religion
        self.gender_law = gender_law
        self.generation = generation
        self.is_progenitor = is_progenitor
        self.is_house = is_house
        self.events = []
        self.father = None
        self.mother = None
        self.skills = {}
        self.education_skill = None
        self.education_tier = None
        self.traits = []
        self.personality_traits = []
        self.congenital_traits = {}
        self.sexuality = None
        self.can_marry = True
        self.assign_sexuality(sexuality_distribution)
        
        # Record birth event
        birth_date_str = generate_random_date(self.birth_year)
        self.birth_year, self.birth_month, self.birth_day = map(int, birth_date_str.split('.'))
        self.add_event(birth_date_str, "birth = yes")

    def siblings(self):
        # Returns a list of siblings (children of the same parents, excluding the character itself)
        siblings = []
        if self.father:
            siblings.extend([child for child in self.father.children if child != self])
        if self.mother:
            siblings.extend([child for child in self.mother.children if child != self])
        return siblings
    
    def assign_sexuality(self, sexuality_distribution):
        """Assign sexuality to the character based on distribution."""
        sexualities = list(sexuality_distribution.keys())
        probabilities = list(sexuality_distribution.values())
        self.sexuality = random.choices(sexualities, probabilities)[0]
        self.can_marry = self.sexuality == 'heterosexual'

    def assign_skills(self, skill_probabilities):
        """Assign skills to the character based on probabilities from config."""
        attributes = ['diplomacy', 'martial', 'stewardship', 'intrigue', 'learning', 'prowess']
        for attribute in attributes:
            self.skills[attribute] = self.random_skill_level(attribute, skill_probabilities)

    def random_skill_level(self, skill_name, skill_probabilities):
        """Randomly select a skill level for a given skill based on probabilities from config."""
        skill_probs = skill_probabilities.get(skill_name, {})
        if not skill_probs:
            logging.warning(f"No skill probabilities defined for {skill_name}. Assigning level 0.")
            return 0
        levels = list(skill_probs.keys())
        probabilities = list(skill_probs.values())
        levels = [int(level) for level in levels]
        return random.choices(levels, probabilities)[0]

    def assign_education(self, education_probabilities, weight_exponent=2):
        """Assign an education trait based on the skills, weighted by their skill levels raised to a power."""
        if not self.skills:
            logging.warning(f"Skills not assigned for {self.char_id}. Cannot assign education.")
            return
        
        # Extract skills and their corresponding levels
        skills = list(self.skills.keys())
        skill_levels = list(self.skills.values())
        
        # Transform the skill levels by raising them to the specified exponent
        transformed_weights = [level ** weight_exponent for level in skill_levels]
        
        # Randomly select a skill based on transformed weights
        selected_skill = random.choices(skills, weights=transformed_weights, k=1)[0]
        logging.debug(f"Character {self.char_id} selected education skill: {selected_skill}")
        
        # Assign education tier based on the selected skill
        self.education_tier = self.random_education_level(selected_skill, education_probabilities)
        self.education_skill = selected_skill  # Store the associated skill

    def random_education_level(self, skill_name, education_probabilities):
        """Randomly select an education level for a given skill based on probabilities from config."""
        edu_probs = education_probabilities.get(skill_name, {})
        if not edu_probs:
            logging.warning(f"No education probabilities defined for {skill_name}. Assigning level 0.")
            return 0
        levels = list(edu_probs.keys())
        probabilities = list(edu_probs.values())
        levels = [int(level) for level in levels]
        return random.choices(levels, probabilities)[0]

    def assign_personality_traits(self, personality_traits_config):
        """Assign personality traits to the character based on weights and mutual exclusions."""
        total_traits = personality_traits_config.get('totalTraitsPerCharacter', 3)
        available_traits = personality_traits_config.copy()
        available_traits.pop('totalTraitsPerCharacter', None)

        trait_pool = list(available_traits.keys())
        trait_weights = [available_traits[trait]['weight'] for trait in trait_pool]

        self.personality_traits = []

        while len(self.personality_traits) < total_traits and trait_pool:
            selected_trait = random.choices(trait_pool, weights=trait_weights, k=1)[0]
            self.personality_traits.append(selected_trait)

            excludes = available_traits[selected_trait].get('excludes', [])
            trait_pool = [trait for trait in trait_pool if trait != selected_trait and trait not in excludes]
            trait_weights = [available_traits[trait]['weight'] for trait in trait_pool]
			
    def add_trait(self, trait):
        """Adds a trait to the character."""
        if trait not in self.traits:
            self.traits.append(trait)

    def add_event(self, event_date, event_detail):
        """Add an event to the character's history."""
        self.events.append((event_date, event_detail))

    def format_for_export(self):
        """Format the character's data and events into CK3 history file format."""
        lines = [f"{self.char_id} = {{"]
        lines.append(f"\tname = {self.name}")
        if self.sex == 'Female':
            lines.append(f"\tfemale = yes")

        # Include culture and religion
        lines.append(f"\tculture = {self.culture}")
        lines.append(f"\treligion = {self.religion}")

        # Collect dynasty and parents information
        sections = []
        if self.dynasty and self.dynasty != "Lowborn":  # Avoid printing "dynasty = Lowborn"
            if self.is_house:
                sections.append(f"\tdynasty_house = {self.dynasty}")
            else:
                sections.append(f"\tdynasty = {self.dynasty}")
        
        if self.father:
            sections.append(f"\tfather = {self.father.char_id}")
        if self.mother:
            sections.append(f"\tmother = {self.mother.char_id}")

        # Add dynasty and parents sections if they exist
        if sections:
            lines.append("")  # Empty line before dynasty/parents
            lines.extend(sections)

        # Always add sexuality with a single empty line before it
        lines.append("")  # Single empty line before sexuality
        lines.append(f"\tsexuality = {self.sexuality}")

        # Include skills
        if self.skills:
            lines.append("")
            for skill, value in self.skills.items():
                lines.append(f"\t{skill} = {value}")

        # Export traits
        if self.traits:
            lines.append("")
            for trait in self.traits:
                lines.append(f"\ttrait = {trait}")
        
        # Include personality traits and education
        if self.personality_traits or self.education_tier is not None or self.congenital_traits:
            lines.append("")
        for trait in self.personality_traits:
            lines.append(f"\ttrait = {trait}")
        if self.education_tier is not None and self.education_skill is not None:
            if self.education_skill == "prowess":
                lines.append(f"\ttrait = education_martial_{self.education_tier}")
            else:
                lines.append(f"\ttrait = education_{self.education_skill}_{self.education_tier}")
        for trait in self.congenital_traits.values():
            lines.append(f"\ttrait = {trait}")

        # Include events
        if self.events:
            lines.append("")
            # Sort events by date
            sorted_events = sorted(self.events, key=lambda e: e[0])
            for event_date, event_detail in sorted_events:
                if event_detail == "birth = yes":
                    lines.append(f"\t{event_date} = {{")
                    lines.append(f"\t    {event_detail}")
                    lines.append(f"\t}}")
                else:
                    # Parse the event date
                    try:
                        event_year, event_month, event_day = map(int, event_date.split('.'))
                    except ValueError:
                        logging.warning(f"Invalid event date format for character {self.char_id}: {event_date}")
                        event_year, event_month, event_day = self.birth_year, self.birth_month, self.birth_day

                    # Calculate age
                    age = event_year - self.birth_year
                    if (event_month, event_day) < (self.birth_month, self.birth_day):
                        age -= 1

                    # Determine event description
                    if event_detail.startswith("add_spouse"):
                        event_desc = f"# Married at age {age}"
                    elif event_detail.startswith("add_matrilineal_spouse"):
                        event_desc = f"# Married at age {age}"
                    elif event_detail.startswith("death"):
                        event_desc = f""
                    else:
                        event_desc = f"# Event at age {age}"

                    # Add event with description
                    lines.append(f"\t{event_date} = {{  {event_desc}")
                    lines.append(f"\t    {event_detail}")
                    lines.append(f"\t}}")

        lines.append(f"}}\n")
        return "\n".join(lines)
    
    