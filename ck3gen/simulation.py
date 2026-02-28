"""
ck3gen/simulation.py
~~~~~~~~~~~~~~~~~~~~
Year-by-year simulation engine for the CK3 Character History Generator.

The Simulation class is the main entry point.  It is constructed with a
loaded config dict and a NameLoader instance, then driven by run_simulation().
"""

from __future__ import annotations

import logging
import random
import re

from ck3gen.character import Character
from utils.utils import generate_random_date, generate_char_id

logger = logging.getLogger(__name__)


class Simulation:
    """Drives the full character simulation from progenitor creation to export."""

    def __init__(self, config: dict, name_loader) -> None:
        self.config = config
        self.name_loader = name_loader
        self.character_count: int = 0
        self.dynasty_char_counters: dict[str, int] = {}
        self.all_characters: list[Character] = []
        self.character_pool: dict[int, list[Character]] = {}
        self.unmarried_males: dict[int, list[Character]] = {}
        self.unmarried_females: dict[int, list[Character]] = {}
        self.couple_last_child_year: dict[tuple[str, str], int] = {}

        self.marriage_max_age_diff: int = config["life_stages"].get("marriageMaxAgeDifference", 5)
        self.marriage_min_age: int = 16
        self.numenor_marriage_inc: int = 5

        # Caches set during _prepare_simulation_vars
        self.desperation_rates: list[float] = config["life_stages"]["desperationMarriageRates"]
        self.marriage_rates: dict = config["life_stages"]["marriageRates"]
        self.fertility_rates: dict = config["life_stages"]["fertilityRates"]
        self.bastardy_chance_male: float = 0.0
        self.bastardy_chance_female: float = 0.0
        self.maximum_children: int = 0
        self.peak_f: float = 0.0
        self.peak_m: float = 0.0
        self.fer_f: list[float] = []
        self.fer_m: list[float] = []

        self.allow_cousin_marriage: dict[str, bool] = {
            d["dynastyID"]: d.get("allowFirstCousinMarriage", False)
            for d in config["initialization"]["dynasties"]
        }

        self.prioritise_lowborn_marriage: dict[str, bool] = {
            d["dynastyID"]: d.get("prioritiseLowbornMarriage", False)
            for d in config["initialization"]["dynasties"]
        }

        self.childhood_by_education: dict[str, list[str]] = {
            "diplomacy":   ["charming", "curious"],
            "intrigue":    ["charming", "rowdy"],
            "martial":     ["rowdy",    "bossy"],
            "stewardship": ["pensive",  "bossy"],
            "learning":    ["pensive",  "curious"],
        }

        self.init_characters()

    # ------------------------------------------------------------------
    #  Initialisation
    # ------------------------------------------------------------------

    def init_characters(self) -> None:
        """Create progenitor characters for every dynasty in the config."""
        sexuality_distribution = self.config["skills_and_traits"]["sexualityDistribution"]

        for dynasty_config in self.config["initialization"]["dynasties"]:
            dynasty_id = dynasty_config["dynastyID"]
            culture = dynasty_config["cultureID"]
            religion = dynasty_config["faithID"]
            gender_law = dynasty_config["gender_law"]
            birth_year = dynasty_config["progenitorMaleBirthYear"]
            blood_tier: int | None = dynasty_config.get("numenorBloodTier")

            dynasty_prefix = dynasty_id.split("_")[1] if "_" in dynasty_id else dynasty_id
            char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)

            progenitor = Character(
                char_id=char_id,
                name=self.name_loader.load_names(culture, "male"),
                sex="Male",
                birth_year=birth_year,
                dynasty=dynasty_id,
                is_house=dynasty_config.get("isHouse", False),
                culture=culture,
                religion=religion,
                gender_law=gender_law,
                sexuality_distribution=sexuality_distribution,
                generation=1,
                is_progenitor=True,
                birth_order=1,
                numenorean_blood_tier=blood_tier,
            )

            progenitor.assign_skills(self.config["skills_and_traits"]["skillProbabilities"])
            progenitor.assign_education(self.config["skills_and_traits"]["educationProbabilities"])
            progenitor.assign_personality_traits(self.config["skills_and_traits"]["personalityTraits"])

            skill = progenitor.education_skill or "diplomacy"
            choices = self.childhood_by_education.get(skill, ["charming", "curious"])
            childhood_trait = random.choice(choices)
            childhood_date = f"{birth_year + 3}.{progenitor.birth_month:02d}.{progenitor.birth_day:02d}"
            progenitor.add_event(childhood_date, f"trait = {childhood_trait}")

            trait_date = f"{birth_year + 16}.{progenitor.birth_month:02d}.{progenitor.birth_day:02d}"
            detail_lines = [f"trait = {t}" for t in progenitor.personality_traits]
            event_detail = "\n    ".join(detail_lines)
            progenitor.add_event(trait_date, event_detail)

            self.add_character_to_pool(progenitor)
            self.all_characters.append(progenitor)

    # ------------------------------------------------------------------
    #  Pool management
    # ------------------------------------------------------------------

    def add_character_to_pool(self, character: Character) -> None:
        """Register a character in the year-indexed pool and apply mortality penalty."""
        mortality_penalty = character.apply_dynasty_mortality_penalty()
        character.mortality_risk += mortality_penalty
        self.character_pool.setdefault(character.birth_year, []).append(character)

    def remove_from_unmarried_pools(self, character: Character) -> None:
        """Remove a character from whichever unmarried pool contains them."""
        age = character.age
        pool = self.unmarried_males if character.sex == "Male" else self.unmarried_females
        if age in pool and character in pool[age]:
            pool[age].remove(character)

    def update_unmarried_pools(self, year: int) -> None:
        """Refresh the unmarried candidate pools for the current year."""
        for char in self.all_characters:
            if not (char.alive and not char.married and char.can_marry):
                continue

            age = char.age
            tier = char.numenorean_blood_tier or 0

            if age < self.marriage_min_age + tier * self.numenor_marriage_inc:
                continue

            sex_rates = self.marriage_rates[char.sex]
            if age >= len(sex_rates) or sex_rates[age] == 0:
                continue

            pool = self.unmarried_males if char.sex == "Male" else self.unmarried_females
            if age not in pool or char not in pool[age]:
                pool.setdefault(age, []).append(char)

    def max_age_diff_for(self, character: Character) -> int:
        """Return the effective maximum age difference for this character."""
        return self.marriage_max_age_diff + 5 * (character.numenorean_blood_tier or 0)

    # ------------------------------------------------------------------
    #  Fertility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_fertile(c: Character) -> bool:
        """Return True if the character is within reproductive age bounds."""
        if not c.alive:
            return False
        if c.sex == "Male":
            return 16 <= c.age <= 70
        return 16 <= c.age <= 45

    def get_extended_fertility_rate(self, character: Character, sex: str) -> float:
        """Return the fertility rate for a character, extending past the table for blooded characters."""
        rates = self.fer_f if sex == "Female" else self.fer_m
        age = character.age
        tier = character.numenorean_blood_tier or 0
        effective_age = max(age - 20 * tier, 0)
        peak = self.peak_f if sex == "Female" else self.peak_m
        if effective_age < len(rates):
            return rates[effective_age]
        return peak if tier > 0 and age <= 45 + 10 * tier else 0.0

    # ------------------------------------------------------------------
    #  Marriage helpers
    # ------------------------------------------------------------------

    def are_siblings(self, char1: Character, char2: Character) -> bool:
        """Return True if char2 is in char1's sibling set."""
        return char2 in char1.siblings()

    def are_first_cousins(self, char1: Character, char2: Character) -> bool:
        """Return True if char1 and char2 share at least one sibling-pair of parents."""
        for p1 in (char1.father, char1.mother):
            for p2 in (char2.father, char2.mother):
                if p1 and p2 and self.are_siblings(p1, p2):
                    return True
        return False

    def pick_partner_by_blood_preference(
        self,
        seeker: Character,
        candidates: list[Character],
    ) -> Character | None:
        """
        Select one candidate according to blood-tier preference rules.

        Blooded seekers prefer the closest-tier blooded partner.
        Non-blooded seekers prefer non-blooded partners, or else the lowest tier.
        """
        if not candidates:
            return None

        t_seek = seeker.numenorean_blood_tier or 0
        if t_seek > 0:
            blooded = [c for c in candidates if (c.numenorean_blood_tier or 0) > 0]
            if blooded:
                best_dist = min(abs(t_seek - (c.numenorean_blood_tier or 0)) for c in blooded)
                best = [c for c in blooded if abs(t_seek - (c.numenorean_blood_tier or 0)) == best_dist]
                return random.choice(best)

        non_blood = [c for c in candidates if (c.numenorean_blood_tier or 0) == 0]
        if non_blood:
            return random.choice(non_blood)

        lowest = min(c.numenorean_blood_tier or 0 for c in candidates)
        best = [c for c in candidates if (c.numenorean_blood_tier or 0) == lowest]
        return random.choice(best)

    def has_dynasty(self, c: Character | None) -> bool:
        """Return True when c exists and belongs to a non-Lowborn dynasty."""
        return bool(c and c.dynasty and c.dynasty != "Lowborn")

    def sibling_index(self, c: Character) -> int:
        """Return the 0-based birth order of c among their parent's children."""
        p = c.father or c.mother
        if not p:
            return 0
        ordered = sorted(
            p.children,
            key=lambda x: (x.birth_year or 0, x.birth_month or 1, x.birth_day or 1),
        )
        try:
            return ordered.index(c)
        except ValueError:
            return len(ordered)

    def dyn_grandparent(self, child: Character) -> Character | None:
        """Return the grandparent who shares the child's dynasty; prefer the senior line."""
        gps = [gp for gp in (child.father, child.mother) if self.has_dynasty(gp) and gp.dynasty == child.dynasty]
        if not gps:
            return None
        if len(gps) == 1:
            return gps[0]
        return min(gps, key=self.sibling_index)

    def elder_of(self, a: Character, b: Character) -> Character:
        """Return the elder-line character between two candidates."""
        ad, bd = self.has_dynasty(a), self.has_dynasty(b)
        if ad and not bd:
            return a
        if bd and not ad:
            return b

        ia, ib = self.sibling_index(a), self.sibling_index(b)
        if ia != ib:
            return a if ia < ib else b

        gpa, gpb = self.dyn_grandparent(a), self.dyn_grandparent(b)
        if gpa and not gpb:
            return a
        if gpb and not gpa:
            return b
        if not gpa and not gpb:
            return a

        return self.elder_of(gpa, gpb)

    def marry_characters(
        self,
        char1: Character,
        char2: Character,
        year: int,
        marriage_type: str | None = None,
        children_dynasty: str | None = None,
    ) -> None:
        """Bind two characters in marriage and record the marriage event."""
        if char1.char_id == char2.char_id:
            logger.info("Attempted self-marriage for %s. Skipping.", char1.char_id)
            return

        if char1.married or char2.married:
            logger.debug(
                "One of the characters is already married: %s, %s. Skipping.",
                char1.char_id,
                char2.char_id,
            )
            return

        if not char1.alive or not char2.alive:
            return

        if not marriage_type:
            if char1.gender_law in ("AGNATIC", "AGNATIC_COGNATIC") and char1.sex == "Male":
                marriage_type = "add_spouse"
                children_dynasty = char1.dynasty
            elif char1.gender_law in ("ENATIC", "ENATIC_COGNATIC") and char1.sex == "Female":
                marriage_type = "add_matrilineal_spouse"
                children_dynasty = char1.dynasty
            else:
                marriage_type = "add_spouse" if char1.sex == "Male" else "add_matrilineal_spouse"
                children_dynasty = char1.dynasty if char1.dynasty else char2.dynasty

        char1.married = True
        char1.spouse = char2
        char2.married = True
        char2.spouse = char1
        char1.marriage_year = year
        char2.marriage_year = year

        self.remove_from_unmarried_pools(char1)
        self.remove_from_unmarried_pools(char2)

        marriage_date = generate_random_date(year)
        char1.add_event(marriage_date, f"{marriage_type} = {char2.char_id}")

    def match_marriages(self, males: list[Character], females: list[Character], year: int) -> None:
        """Attempt to pair eligible males with eligible females."""
        dynasty_sizes: dict[str, int] = {dyn: 0 for dyn in {c.dynasty for c in self.all_characters if c.dynasty}}
        for character in self.all_characters:
            if character.alive:
                dynasty_sizes[character.dynasty] = dynasty_sizes.get(character.dynasty, 0) + 1

        males.sort(key=lambda c: (dynasty_sizes.get(c.dynasty, 0), c.birth_order if c.birth_order is not None else float("inf")))
        females.sort(key=lambda c: (dynasty_sizes.get(c.dynasty, 0), c.birth_order if c.birth_order is not None else float("inf")))

        for male in males:
            if not male.alive or male.married or not male.can_marry:
                continue

            if self.prioritise_lowborn_marriage.get(male.dynasty, False) and random.random() < 0.6:
                self.generate_lowborn_and_marry(male, year)
                continue

            available_females = [
                f for f in females
                if (
                    f.alive
                    and not f.married
                    and f.can_marry
                    and (f.dynasty != male.dynasty or f.dynasty is None)
                    and not self.are_siblings(male, f)
                    and (
                        self.allow_cousin_marriage.get(male.dynasty, False)
                        or not self.are_first_cousins(male, f)
                    )
                    and abs(f.age - male.age) <= max(self.max_age_diff_for(male), self.max_age_diff_for(f))
                )
            ]

            if available_females:
                female = self.pick_partner_by_blood_preference(male, available_females)
                self.marry_characters(male, female, year)
                continue

            # Fallback: same-dynasty marriage
            available_females = [
                f for f in females
                if (
                    f.alive
                    and not f.married
                    and f.can_marry
                    and f.dynasty == male.dynasty
                    and not self.are_siblings(male, f)
                    and (
                        self.allow_cousin_marriage.get(male.dynasty, False)
                        or not self.are_first_cousins(male, f)
                    )
                    and abs(f.age - male.age) <= max(self.max_age_diff_for(male), self.max_age_diff_for(f))
                )
            ]

            if available_females:
                female = self.pick_partner_by_blood_preference(male, available_females)
                self.marry_characters(male, female, year)
                continue

            self.desperation_marriage_check(male, year)

    def desperation_marriage_check(self, male: Character, year: int) -> bool:
        """Attempt a desperation marriage for a male character; return True if paired."""
        age = male.age
        if age >= len(self.desperation_rates):
            return False

        if random.random() < self.desperation_rates[age]:
            self.generate_lowborn_and_marry(male, year)
            return True

        return False

    def generate_lowborn_and_marry(self, character: Character, year: int) -> None:
        """Create a lowborn spouse and marry them to the given character."""
        culture = character.culture
        spouse_sex = "Male" if character.sex == "Female" else "Female"
        # Name files use title-cased gender strings (e.g. "Male", "Female")
        spouse_name = self.name_loader.load_names(culture, spouse_sex.capitalize())

        dynasty_prefix = character.dynasty.split("_")[1] if "_" in character.dynasty else "lowborn"
        spouse_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)

        spouse_kwargs: dict = dict(
            char_id=spouse_char_id,
            name=spouse_name,
            sex=spouse_sex,
            birth_year=year - random.randint(18, 26),
            dynasty=None,
            is_house=False,
            culture=character.culture,
            religion=character.religion,
            gender_law=character.gender_law,
            sexuality_distribution=self.config["skills_and_traits"]["sexualityDistribution"],
            generation=character.generation,
            is_progenitor=False,
            birth_order=1,
        )
        if character.numenorean_blood_tier:
            spouse_kwargs["numenorean_blood_tier"] = character.numenorean_blood_tier

        spouse = Character(**spouse_kwargs)
        self.add_character_to_pool(spouse)
        self.all_characters.append(spouse)

        spouse.assign_skills(self.config["skills_and_traits"]["skillProbabilities"])
        spouse.assign_education(self.config["skills_and_traits"]["educationProbabilities"])
        spouse.assign_personality_traits(self.config["skills_and_traits"]["personalityTraits"])

        skill = spouse.education_skill or "diplomacy"
        choices = self.childhood_by_education.get(skill, ["charming", "curious"])
        trait = random.choice(choices)
        childhood_date = f"{spouse.birth_year + 3}.{spouse.birth_month:02d}.{spouse.birth_day:02d}"
        spouse.add_event(childhood_date, f"trait = {trait}")

        trait_date = f"{spouse.birth_year + 16}.{spouse.birth_month:02d}.{spouse.birth_day:02d}"
        detail_lines = [f"trait = {t}" for t in spouse.personality_traits]
        event_detail = "\n    ".join(detail_lines)
        spouse.add_event(trait_date, event_detail)

        spouse_dynasty = character.dynasty
        self.marry_characters(character, spouse, year, children_dynasty=spouse_dynasty)

    # ------------------------------------------------------------------
    #  Child creation
    # ------------------------------------------------------------------

    def _death_cause(self, character: Character) -> str:
        """Return the appropriate CK3 death reason string for a character."""
        if character.negativeEventDeathReason is not None:
            return character.negativeEventDeathReason
        if character.age > 65 + 20 * (character.numenorean_blood_tier or 0):
            return "death_natural_causes"
        if character.age < 18:
            return "death_ill"
        if character.sex == "Male":
            return random.choice([
                "death_ill", "death_cancer", "death_battle", "death_attacked",
                "death_accident", "death_murder", "death_natural_causes",
                "death_drinking_passive", "death_dungeon_passive",
            ])
        return random.choice(["death_ill", "death_cancer", "death_accident", "death_murder"])

    def create_child(self, mother: Character, father: Character, birth_year: int) -> Character | None:
        """Attempt to create a child for a married couple; return None if ineligible."""
        maximum_children = self.config["life_stages"]["maximumNumberOfChildren"]
        if len(mother.children) >= maximum_children:
            return None

        couple_key = (father.char_id, mother.char_id)
        last_birth_year = self.couple_last_child_year.get(couple_key)
        min_years = self.config["life_stages"]["minimumYearsBetweenChildren"]
        if last_birth_year is not None and birth_year < last_birth_year + min_years:
            return None

        self.character_count += 1
        child_generation = max(mother.generation, father.generation) + 1
        if child_generation > self.config["initialization"]["generationMax"]:
            return None

        # Gender preference based on inheritance law
        gender_preference: str | None = None
        if father.gender_law in ("AGNATIC", "AGNATIC_COGNATIC"):
            gender_preference = "Male"
        elif mother.gender_law in ("ENATIC", "ENATIC_COGNATIC"):
            gender_preference = "Female"

        siblings = mother.children + father.children
        has_male = any(s.sex == "Male" for s in siblings)
        has_female = any(s.sex == "Female" for s in siblings)

        if gender_preference == "Male" and not has_male:
            male_chance = 0.9
        elif gender_preference == "Female" and not has_female:
            male_chance = 0.1
        else:
            male_chance = 0.5

        child_sex = "Male" if random.random() < male_chance else "Female"

        # Dynasty, culture, religion from the elder parent line
        if mother.gender_law in ("AGNATIC", "AGNATIC_COGNATIC") and father.gender_law in ("AGNATIC", "AGNATIC_COGNATIC"):
            child_dynasty, child_is_house, child_culture, child_religion, child_gender_law = (
                father.dynasty, father.is_house, father.culture, father.religion, father.gender_law
            )
        elif mother.gender_law in ("ENATIC", "ENATIC_COGNATIC") and mother.sex == "Female":
            child_dynasty, child_is_house, child_culture, child_religion, child_gender_law = (
                mother.dynasty, mother.is_house, mother.culture, mother.religion, mother.gender_law
            )
        else:
            elder = self.elder_of(mother, father)
            if elder is father:
                child_dynasty, child_is_house, child_culture, child_religion, child_gender_law = (
                    father.dynasty, father.is_house, father.culture, father.religion, father.gender_law
                )
            else:
                child_dynasty, child_is_house, child_culture, child_religion, child_gender_law = (
                    mother.dynasty, mother.is_house, mother.culture, mother.religion, mother.gender_law
                )

        dynasty_prefix = child_dynasty.split("_")[1] if child_dynasty and "_" in child_dynasty else "lowborn"
        child_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)
        child_name = self.assign_child_name(child_sex, mother, father, child_dynasty)
        sexuality_distribution = self.config["skills_and_traits"]["sexualityDistribution"]
        birth_order = len(mother.children) + 1

        # Birth-order fertility scaling
        _BIRTH_ORDER_MODIFIERS: dict[int, float] = {1: 1.0, 2: 0.80, 3: 0.60, 4: 0.40, 5: 0.20}
        fertility_modifier = _BIRTH_ORDER_MODIFIERS.get(birth_order, 0.10)

        alive_fertile = sum(
            1 for c in self.all_characters
            if c.dynasty == child_dynasty and c.alive and self._is_fertile(c)
        )
        if alive_fertile > 8:
            if child_sex == "Male" and father.fertilityModifier != 1:
                fertility_modifier *= father.fertilityModifier
            elif child_sex == "Female" and mother.fertilityModifier != 1:
                fertility_modifier *= mother.fertilityModifier
        else:
            fertility_modifier = 1.0

        if father.dynasty == child_dynasty and self.prioritise_lowborn_marriage.get(father.dynasty, False):
            fertility_modifier *= father.fertilityModifier * 0.65
        elif mother.dynasty == child_dynasty and self.prioritise_lowborn_marriage.get(mother.dynasty, False):
            fertility_modifier *= mother.fertilityModifier * 0.65

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
            birth_order=birth_order,
            fertilityModifier=fertility_modifier,
        )

        inherit_params = self.config.get("initialization", {}).get("numenorInheritance", {})
        decline_table = self.config.get("initialization", {}).get("numenorDecline", {})
        Character.inherit_numenorean_blood(child, father, mother, inherit_params, decline_table)

        child.father = father if father.sex == "Male" else mother
        child.mother = mother if mother.sex == "Female" else father
        mother.children.append(child)
        father.children.append(child)

        child.assign_skills(self.config["skills_and_traits"]["skillProbabilities"])
        child.assign_education(self.config["skills_and_traits"]["educationProbabilities"])
        Character.inherit_congenital(child, father, mother)

        self.couple_last_child_year[couple_key] = birth_year
        return child

    def create_bastard_child(self, parent: Character, birth_year: int, is_male: bool) -> Character | None:
        """Create an illegitimate child from a single parent."""
        maximum_children = self.config["life_stages"]["maximumNumberOfChildren"]
        if len(parent.children) >= maximum_children:
            return None

        if parent.sex == "Female":
            fer_rates = self.config["life_stages"]["fertilityRates"]["Female"]
            rate = fer_rates[parent.age] if parent.age < len(fer_rates) else 0.0
            if rate == 0.0:
                return None

        self.character_count += 1
        child_generation = parent.generation + 1
        if child_generation > self.config["initialization"]["generationMax"]:
            return None

        gender_preference: str | None = None
        if parent.gender_law in ("AGNATIC", "AGNATIC_COGNATIC"):
            gender_preference = "Male"
        elif parent.gender_law in ("ENATIC", "ENATIC_COGNATIC"):
            gender_preference = "Female"

        siblings = parent.children
        has_male = any(s.sex == "Male" for s in siblings)
        has_female = any(s.sex == "Female" for s in siblings)

        if gender_preference == "Male" and not has_male:
            male_chance = 0.65
        elif gender_preference == "Female" and not has_female:
            male_chance = 0.35
        else:
            male_chance = 0.5

        child_sex = "Male" if random.random() < male_chance else "Female"
        child_dynasty = parent.dynasty
        child_is_house = parent.is_house
        child_culture = parent.culture
        child_religion = parent.religion
        child_gender_law = parent.gender_law

        dynasty_prefix = child_dynasty.split("_")[1] if child_dynasty and "_" in child_dynasty else "lowborn"
        child_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)
        child_name = self.assign_child_name(child_sex, parent, parent, child_dynasty)
        sexuality_distribution = self.config["skills_and_traits"]["sexualityDistribution"]
        birth_order = len(parent.children) + 1

        adjusted_birth_year = max(birth_year, parent.birth_year + 16)

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
            birth_order=birth_order,
        )

        if is_male:
            child.father = parent
            child.mother = None
        else:
            child.mother = parent
            child.father = None
        parent.children.append(child)

        inherit_params = self.config.get("initialization", {}).get("numenorInheritance", {})
        decline_table = self.config.get("initialization", {}).get("numenorDecline", {})
        Character.inherit_numenorean_blood(child, child.father, child.mother, inherit_params, decline_table)

        child.add_trait("bastard")
        child.assign_skills(self.config["skills_and_traits"]["skillProbabilities"])
        child.assign_education(self.config["skills_and_traits"]["educationProbabilities"])
        child.assign_personality_traits(self.config["skills_and_traits"]["personalityTraits"])

        skill = child.education_skill or "diplomacy"
        choices = self.childhood_by_education.get(skill, ["charming", "curious"])
        childhood_date = f"{adjusted_birth_year + 3}.{child.birth_month:02d}.{child.birth_day:02d}"
        child.add_event(childhood_date, f"trait = {random.choice(choices)}")

        trait_date = f"{adjusted_birth_year + 16}.{child.birth_month:02d}.{child.birth_day:02d}"
        detail_lines = [f"trait = {t}" for t in child.personality_traits]
        child.add_event(trait_date, "\n    ".join(detail_lines))

        return child

    # ------------------------------------------------------------------
    #  Name assignment
    # ------------------------------------------------------------------

    def assign_child_name(
        self,
        child_sex: str,
        mother: Character,
        father: Character,
        child_dynasty: str,
    ) -> str:
        """Return a name for a new child based on dynasty inheritance rules."""
        dynasties = self.config.get("initialization", {}).get("dynasties", [])
        current_dynasty = next((d for d in dynasties if d["dynastyID"] == child_dynasty), None)

        if not current_dynasty:
            logger.warning("Dynasty '%s' not found. Assigning random name.", child_dynasty)
            return self.ensure_unique_name(mother, father, child_sex)

        chances = current_dynasty["nameInheritance"]
        options = ["grandparent", "parent", "none"]
        probabilities = [
            chances["grandparentNameInheritanceChance"],
            chances["parentNameInheritanceChance"],
            chances["noNameInheritanceChance"],
        ]
        chosen = random.choices(options, probabilities)[0]

        if chosen == "grandparent":
            if child_sex == "Male":
                grandparent = father.father if father else None
            else:
                grandparent = mother.mother if mother else None
            if grandparent:
                return grandparent.name

        if chosen == "parent":
            return father.name if child_sex == "Male" else mother.name

        return self.ensure_unique_name(mother, father, child_sex)

    def ensure_unique_name(self, mother: Character, father: Character, child_sex: str) -> str:
        """Return a unique name when possible, falling back to any random name."""
        # Name files use title-cased gender strings (e.g. "Male", "Female")
        existing = {c.name for c in mother.children + father.children if c.alive}
        unique = self.name_loader.get_all_names(mother.culture, child_sex.capitalize())
        available = [n for n in unique if n not in existing]

        if available:
            name = random.choice(available)
            logger.debug("Assigned unique random name: %s", name)
            return name

        name = self.name_loader.load_names(mother.culture, child_sex.capitalize())
        logger.warning("No unique names available. Assigned random name: %s", name)
        return name

    # ------------------------------------------------------------------
    #  Bastardy
    # ------------------------------------------------------------------

    def handle_bastardy(
        self,
        year: int,
        bastardy_chance_male: float,
        bastardy_chance_female: float,
        fertility_rates: dict,
    ) -> None:
        """Generate illegitimate children for eligible noble characters."""
        father_bastard_done: set[str] = set()

        for character in self.all_characters:
            if not character.alive or not character.dynasty or character.dynasty == "Lowborn":
                continue

            if character.sex == "Female":
                fertility_rate = (
                    self.get_extended_fertility_rate(character, "Female")
                    * character.fertility_mult()
                )
                if fertility_rate == 0.0:
                    continue

                couple_key = (character.spouse.char_id, character.char_id) if character.married and character.spouse else None
                if couple_key and self.couple_last_child_year.get(couple_key, -1) == year:
                    continue

                if random.random() < bastardy_chance_female:
                    child = self.create_bastard_child(character, year, is_male=False)
                    if child:
                        self.add_character_to_pool(child)
                        self.all_characters.append(child)

            elif character.sex == "Male":
                if character.char_id in father_bastard_done:
                    continue
                if random.random() < bastardy_chance_male:
                    child = self.create_bastard_child(character, year, is_male=True)
                    if child:
                        self.add_character_to_pool(child)
                        self.all_characters.append(child)
                        father_bastard_done.add(character.char_id)

    # ------------------------------------------------------------------
    #  Death
    # ------------------------------------------------------------------

    def character_death_check(self, character: Character) -> bool:
        """Return True if the character should die this year."""
        if character.is_progenitor and character.age < 50:
            return False

        tier = character.numenorean_blood_tier or 0
        effective_age = max(character.age - 20 * tier, 0)
        effective_age = min(effective_age, 120)

        sex = character.sex
        birth_year = character.birth_year
        mortality_rates = self.config["life_stages"]["mortalityRates"][sex]

        if effective_age < 1:
            mortality_rate = 0.0
        elif effective_age < len(mortality_rates):
            mortality_rate = mortality_rates[effective_age]
        else:
            mortality_rate = 1.0

        mortality_event_multiplier = 1.0
        for event in self.config.get("initialization", {}).get("events", []):
            if (
                birth_year >= event.get("startYear")
                and birth_year <= event.get("endYear")
                and character.age >= event.get("characterAgeStart")
                and character.age <= event.get("characterAgeEnd")
            ):
                mortality_event_multiplier = 1.0 - event.get("deathMultiplier", 0.0)
                character.negativeEventDeathReason = event.get("deathReason")

        random_var = random.random()
        if self.prioritise_lowborn_marriage.get(character.dynasty, False):
            random_var *= 0.35

        return (random_var * mortality_event_multiplier) < mortality_rate

    # ------------------------------------------------------------------
    #  Simulation loop
    # ------------------------------------------------------------------

    def _prepare_simulation_vars(self) -> None:
        """Cache frequently accessed config values as instance attributes."""
        life_stages = self.config["life_stages"]
        self.desperation_rates = life_stages.get("desperationMarriageRates", [0.0] * 121)
        self.marriage_rates = life_stages["marriageRates"]
        self.fertility_rates = life_stages["fertilityRates"]
        self.bastardy_chance_male = life_stages["bastardyChanceMale"]
        self.bastardy_chance_female = life_stages["bastardyChanceFemale"]
        self.maximum_children = life_stages["maximumNumberOfChildren"]

        fer_f = self.fertility_rates["Female"]
        fer_m = self.fertility_rates["Male"]
        self.peak_f = max(fer_f[16:]) if len(fer_f) > 16 else 0.0
        self.peak_m = max(fer_m[16:]) if len(fer_m) > 16 else 0.0
        self.fer_f = fer_f
        self.fer_m = fer_m

    def _process_yearly_updates(self, year: int) -> None:
        """Update ages and fire age-gated trait events for all living characters."""
        for character in self.all_characters:
            character.negativeEventDeathReason = None  # Reset per-year event death reason
            if not character.alive:
                continue

            character.age = max(year - character.birth_year, 0)

            if character.age == 3:
                skill = character.education_skill or "diplomacy"
                choices = self.childhood_by_education.get(skill, ["charming", "curious"])
                date = f"{year}.{character.birth_month:02d}.{character.birth_day:02d}"
                character.add_event(date, f"trait = {random.choice(choices)}")

            if character.age == 16 and not character.personality_traits:
                character.assign_personality_traits(self.config["skills_and_traits"]["personalityTraits"])
                date = f"{year}.{character.birth_month:02d}.{character.birth_day:02d}"
                detail_lines = [f"trait = {t}" for t in character.personality_traits]
                character.add_event(date, "\n    ".join(detail_lines))

    def _process_marriages(self, year: int) -> None:
        """Refresh marriage pools and match eligible couples."""
        self.unmarried_males.clear()
        self.unmarried_females.clear()
        self.update_unmarried_pools(year)

        all_males = [m for males in self.unmarried_males.values() for m in males]
        all_females = [f for females in self.unmarried_females.values() for f in females]

        if all_males and all_females:
            self.match_marriages(all_males, all_females, year)

    def _process_births(self, year: int) -> None:
        """Handle births from married couples and bastardy events."""
        for character in self.all_characters:
            if not (character.alive and character.married and character.sex == "Female"):
                continue

            if len(character.children) >= self.maximum_children:
                continue

            fertility_rate = (
                self.get_extended_fertility_rate(character, "Female")
                * character.fertility_mult()
            )
            fertility_rate_m = (
                self.get_extended_fertility_rate(character.spouse, "Male")
                * character.spouse.fertility_mult()
            )

            if random.random() < fertility_rate * fertility_rate_m:
                child = self.create_child(character, character.spouse, year)
                if child:
                    self.add_character_to_pool(child)
                    self.all_characters.append(child)

        self.handle_bastardy(year, self.bastardy_chance_male, self.bastardy_chance_female, self.fertility_rates)

    def _process_deaths(self, year: int) -> None:
        """Check for and process character deaths."""
        for character in self.all_characters:
            if not character.alive:
                continue

            if self.character_death_check(character):
                character.alive = False
                death_date = generate_random_date(year)
                character.death_year, character.death_month, character.death_day = map(int, death_date.split("."))

                self.remove_from_unmarried_pools(character)

                death_cause = self._death_cause(character)
                character.add_event(death_date, f"death = {{ death_reason = {death_cause} }}")

                # Widen the surviving spouse to an unmarried state
                if character.married and character.spouse and character.spouse.alive:
                    character.spouse.married = False
                    character.spouse.spouse = None

    def _process_survivor_deaths(self, last_sim_year: int) -> None:
        """Estimate post-simulation death dates for all characters still alive."""
        survivors = [c for c in self.all_characters if c.alive]
        if not survivors:
            return

        logger.info("Estimating death dates for %d survivors...", len(survivors))

        year = last_sim_year
        while survivors:
            year += 1
            for i in range(len(survivors) - 1, -1, -1):
                character = survivors[i]
                character.age = year - character.birth_year
                character.negativeEventDeathReason = None

                if self.character_death_check(character):
                    character.alive = False
                    death_date = generate_random_date(year)
                    character.death_year, character.death_month, character.death_day = map(int, death_date.split("."))

                    death_cause = self._death_cause(character)
                    character.add_event(death_date, f"death = {{ death_reason = {death_cause} }}")

                    survivors.pop(i)

    def run_simulation(self) -> None:
        """Execute the main year-by-year simulation loop."""
        self._prepare_simulation_vars()

        min_year = self.config["initialization"]["minYear"]
        max_year = self.config["initialization"]["maxYear"]

        for year in range(min_year, max_year + 1):
            self._process_yearly_updates(year)
            self._process_marriages(year)
            self._process_births(year)
            self._process_deaths(year)
            self.update_unmarried_pools(year)

        logger.info("Main simulation loop complete. Processing survivors...")
        self._process_survivor_deaths(max_year)

    # ------------------------------------------------------------------
    #  Export
    # ------------------------------------------------------------------

    def export_characters(self, output_filename: str = "family_history.txt") -> None:
        """Write all character history data to the output directory."""
        from ck3gen.paths import CHARACTER_OUTPUT_DIR  # noqa: PLC0415

        CHARACTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = CHARACTER_OUTPUT_DIR / output_filename

        dynasty_groups: dict[str, list[Character]] = {}

        for character in self.all_characters:
            if not character.dynasty:
                continue
            if character.spouse and character.dynasty == "Lowborn":
                dynasty = (
                    character.spouse.dynasty
                    if character.spouse.dynasty != "Lowborn"
                    else character.dynasty
                )
            else:
                dynasty = character.dynasty

            dynasty_groups.setdefault(dynasty, []).append(character)

        exported_count = 0
        with open(output_path, "w", encoding="utf-8") as file:
            for dynasty, characters in sorted(dynasty_groups.items()):
                file.write("################\n")
                file.write(f"### Dynasty {dynasty}\n")
                file.write("################\n\n")
                for character in sorted(characters, key=lambda c: int(re.sub(r"\D", "", c.char_id))):
                    file.write(character.format_for_export())
                    file.write("\n")
                    exported_count += 1

        logger.info("Character history exported to %s", output_path)
        logger.info("Total characters exported: %d", exported_count)