import random
import logging
from utils.utils import generate_random_date

# ==============================================================
# Congenital‑trait helper (beauty / intellect / physique)
# ==============================================================

_CONGENITAL_TIERS = {
    "beauty": [
        "beauty_bad_3", "beauty_bad_2", "beauty_bad_1",
        "beauty_good_1", "beauty_good_2", "beauty_good_3",
    ],
    "intellect": [
        "intellect_bad_3", "intellect_bad_2", "intellect_bad_1",
        "intellect_good_1", "intellect_good_2", "intellect_good_3",
    ],
    "physique": [
        "physique_bad_3", "physique_bad_2", "physique_bad_1",
        "physique_good_1", "physique_good_2", "physique_good_3",
    ],
}

# mutation odds in order  bad3..bad1, good1..good3
_RANDOM_PICK_CHANCE = [0.0015, 0.0025, 0.005, 0.005, 0.0025, 0.0015]


def _tier_index(trait: str, category: str) -> int | None:
    """Return tier index (0..5) or None if trait not in this category."""
    try:
        return _CONGENITAL_TIERS[category].index(trait)
    except ValueError:
        return None


def _parent_trait_idx(parent: "Character", category: str) -> int | None:
    """Index of this parent’s trait for category (if any)."""
    for t in parent.congenital_traits.values():
        idx = _tier_index(t, category)
        if idx is not None:
            return idx
    return None


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
        is_bastard=False,
        birth_order=1,  # Add birth_order as an argument
        negativeEventDeathReason=None,
        fertilityModifier=1
    ):
        self.is_bastard = is_bastard
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
        self.gender_law = gender_law if gender_law in ["AGNATIC", "AGNATIC_COGNATIC", "ABSOLUTE_COGNATIC", "ENATIC_COGNATIC", "ENATIC"] else "AGNATIC_COGNATIC"
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
        self.mortality_risk = 0  # Initialize mortality risk
        self.negativeEventDeathReason=None
        self.fertilityModifier = fertilityModifier
        self.numenorean_blood_tier: int | None = None
        
        # Set the birth order if provided, otherwise default to 1
        self.birth_order = birth_order
        
        # Record birth event
        birth_date_str = generate_random_date(self.birth_year)
        self.birth_year, self.birth_month, self.birth_day = map(int, birth_date_str.split('.'))
        self.add_event(birth_date_str, "birth = yes")

    def apply_dynasty_mortality_penalty(self):
        """ Increase mortality risk for distant branches (4+ generations away) """
        if self.generation >= 4:
            return 0.2 * (self.generation - 3)  # Increasing penalty per generation
        return 0.0

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

    # ------------------------------------------------------------------
    #  Congenital‑trait inheritance (beauty / intellect / physique + singles)
    # ------------------------------------------------------------------
    @staticmethod
    def inherit_congenital(child: "Character",
                           father: "Character",
                           mother: "Character") -> None:
        """
        Populate child.congenital_traits with inherited or random
        beauty / intellect / physique tiers **and** single‑tier defects.
        """

        # ── tiered categories -------------------------------------------------
        for category, tiers in _CONGENITAL_TIERS.items():
            idx_f = _parent_trait_idx(father, category)
            idx_m = _parent_trait_idx(mother, category)

            if idx_f is None and idx_m is None:
                best_parent_idx = None
            else:
                best_parent_idx = max(idx for idx in (idx_f, idx_m) if idx is not None)

            # build search order
            if best_parent_idx is None:               # no parent trait → skip to mutation
                idx_sequence = []
            elif best_parent_idx <= 2:                # parent’s best on bad side
                idx_sequence = range(best_parent_idx, 3)           # 0→1→2
            else:                                     # parent’s best on good side
                idx_sequence = range(best_parent_idx, -1, -1)      # 5→…→0

            inherited = False
            for idx in idx_sequence:
                trait_name = tiers[idx]
                father_has = idx_f == idx
                mother_has = idx_m == idx

                # inheritance chance
                if father_has and mother_has:
                    chance = 0.80
                elif father_has or mother_has:
                    other_idx = idx_m if father_has else idx_f
                    same_side_lower = (
                        other_idx is not None
                        and other_idx < idx
                        and other_idx // 3 == idx // 3
                    )
                    chance = 0.50 if same_side_lower else 0.25
                else:                                   # neither parent has tier
                    chance = 0.10

                if random.random() < chance:
                    child.congenital_traits[category] = trait_name
                    inherited = True
                    break

                # stop after failing good_1 when no parent owns any bad tier
                if (
                    idx == 3
                    and best_parent_idx >= 3
                    and (idx_f is None or idx_f > 2)
                    and (idx_m is None or idx_m > 2)
                ):
                    break

            # random mutation if nothing inherited
            if not inherited:
                rnd = random.random()
                cumulative = 0.0
                for idx, prob in enumerate(_RANDOM_PICK_CHANCE):
                    cumulative += prob
                    if rnd < cumulative:
                        child.congenital_traits[category] = tiers[idx]
                        break

        # ── single‑tier congenital traits ------------------------------------
        SINGLE_TRAITS = [
            "clubfooted", "hunchbacked", "lisping", "stuttering",
            "dwarf", "giant", "spindly", "scaly", "albino",
            "wheezing", "bleeder","fecund", "infertile"
        ]
        MUTEX_GROUPS = [
            {"dwarf", "giant"},
            {"fecund", "infertile"}
        ]
        # helper to test exclusivity
        def _conflicts(t: str) -> bool:
            for grp in MUTEX_GROUPS:
                if t in grp and grp & set(child.congenital_traits.values()):
                    return True
            return False

        for trait in SINGLE_TRAITS:
            father_has = trait in father.congenital_traits.values()
            mother_has = trait in mother.congenital_traits.values()

            if father_has and mother_has:
                chance = 0.80
            elif father_has or mother_has:
                chance = 0.25
            else:
                chance = 0.0

            inherited = False
            if chance and random.random() < chance:
                if not _conflicts(trait):
                    child.congenital_traits[trait] = trait
                    inherited = True

            # mutation roll if not inherited
            if not inherited and random.random() < 0.005:      # 0.5 %
                if not _conflicts(trait):
                    child.congenital_traits[trait] = trait

    def fertility_mult(self) -> float:
        """
        Returns a multiplier (0, 1, 2 …) that should be
        applied to the base fertility rate at character.age.
        """
        if "infertile" in self.congenital_traits.values():
            return 0.0
        mult = 1.0 * self.fertilityModifier
        if "fecund" in self.congenital_traits.values():
            mult *= 2.0
        return mult
    
    @staticmethod
    def inherit_numenorean_blood(child: "Character", father: "Character", mother: "Character", params: dict) -> None:
        
        """
        Decide child.numenorean_blood_tier based on parents & configured chances:
          - sameTierChance  if tf == tm
          - closeTierChance if 1 <= |tf-tm| <= 2
          - farTierChance   if |tf-tm| > 2
        On failure, drop by 1 tier (or 2 tiers, for the far case).
        """

        # handle None parents gracefully
        tf = (father.numenorean_blood_tier if father and father.numenorean_blood_tier else 0)
        tm = (mother.numenorean_blood_tier if mother and mother.numenorean_blood_tier else 0)


        # no blood at all → nothing to do
        if tf == 0 and tm == 0:
            return

        high, low = max(tf, tm), min(tf, tm)
        diff = high - low

        if diff == 0:
            chance = params["sameTierChance"]
            drop   = 1
        elif diff <= 2:
            chance = params["closeTierChance"]
            drop   = 1
        else:
            chance = params["farTierChance"]
            drop   = 2

        if random.random() < chance:
            child.numenorean_blood_tier = high
        else:
            # ensure we never go below tier 1
            child.numenorean_blood_tier = max(high - drop, 1)
			
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
        if getattr(self, "numenorean_blood_tier", None):
            tier = self.numenorean_blood_tier
            if 1 <= tier <= 10:
                lines.append("")
                lines.append(f"\ttrait = blood_of_numenor_{tier}")

        # Include events
        if self.events:
            lines.append("")
            # Sort events by date
            sorted_events = sorted(self.events, key=lambda e: e[0])
            for event_date, event_detail in sorted_events:
                if event_detail == "birth = yes":
                    lines.append(f"\t{event_date} = {{")
                    lines.append(f"\t    {event_detail}")

                    # ---------- language effect block ----------
                    lang_effects = []
                    # use the class attribute via self.*
                    for lang, start, end in self.DYNASTY_LANGUAGE_RULES.get(self.dynasty, []):
                        if start <= self.birth_year <= end:
                            lang_effects.append(lang)

                    if lang_effects:                # only if at least one language applies
                        lines.append(f"\t    effect = {{")
                        for l in lang_effects:
                            lines.append(f"\t        learn_language = {l}")
                        lines.append(f"\t    }}")
                    # -------------------------------------------

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
    
    