"""
ck3gen/simulation.py
~~~~~~~~~~~~~~~~~~~~
Year-by-year character history simulation engine.

Orchestrates the full lifecycle of all dynasties:
  - Progenitor seeding
  - Annual age updates and age-gated trait events
  - Marriage matching (noble-to-noble and desperation lowborn marriages)
  - Births (legitimate and illegitimate)
  - Deaths (event-driven and age-based mortality)
  - Post-simulation survivor death estimation
  - Character history export
"""

from __future__ import annotations

import logging
import os
import random
import re
from typing import Optional

from ck3gen.character import Character
from ck3gen.paths import CHARACTER_OUTPUT_DIR
from utils.utils import generate_char_id, generate_random_date

logger = logging.getLogger(__name__)


class Simulation:
    """Drives the full character history simulation for all configured dynasties."""

    def __init__(self, config: dict, name_loader) -> None:
        self.config = config
        self.name_loader = name_loader

        self.current_char_id: int = self.config["initialization"]["initialCharID"]
        self.character_count: int = 0
        self.dynasty_char_counters: dict[str, int] = {}

        self.all_characters: list[Character] = []
        self.character_pool: dict[int, list[Character]] = {}
        self.unmarried_males: dict[int, list[Character]] = {}
        self.unmarried_females: dict[int, list[Character]] = {}
        self.couple_last_child_year: dict[tuple[str, str], int] = {}

        life_stages = self.config["life_stages"]
        self.marriage_max_age_diff: int = life_stages.get("marriageMaxAgeDifference", 5)
        self.marriage_min_age: int = 16
        self.numenor_marriage_inc: int = 5
        self.marriage_rates: dict = life_stages["marriageRates"]
        self.desperation_rates: list[float] = life_stages["desperationMarriageRates"]

        dynasties_cfg: list[dict] = config["initialization"]["dynasties"]
        self.allow_cousin_marriage: dict[str, bool] = {
            d["dynastyID"]: d.get("allowFirstCousinMarriage", False)
            for d in dynasties_cfg
        }
        self.prioritise_lowborn_marriage: dict[str, bool] = {
            d["dynastyID"]: d.get("prioritiseLowbornMarriage", False)
            for d in dynasties_cfg
        }
        self.force_dynasty_alive: dict[str, bool] = {
            d["dynastyID"]: d.get("forceDynastyAlive", False)
            for d in dynasties_cfg
        }

        # Maps each education skill to two possible childhood trait strings.
        self.childhood_by_education: dict[str, list[str]] = {
            "diplomacy":   ["charming", "curious"],
            "intrigue":    ["charming", "rowdy"],
            "martial":     ["rowdy",    "bossy"],
            "stewardship": ["pensive",  "bossy"],
            "learning":    ["pensive",  "curious"],
        }

        # Seed one male progenitor per dynasty before the simulation loop begins.
        self._seed_progenitors()

    # ------------------------------------------------------------------
    #  Progenitor seeding
    # ------------------------------------------------------------------

    def _seed_progenitors(self) -> None:
        """Create and register the founding character for every configured dynasty."""
        dynasties: list[dict] = self.config["initialization"].get("dynasties", [])
        skills_cfg: dict = self.config["skills_and_traits"]

        for dynasty in dynasties:
            dynasty_id: str = dynasty["dynastyID"]
            culture: str = dynasty["cultureID"]
            religion: str = dynasty["faithID"]
            gender_law: str = dynasty["gender_law"]
            is_house: bool = dynasty.get("isHouse", False)
            blood_tier: Optional[int] = dynasty.get("numenorBloodTier", None)
            birth_year: int = dynasty["progenitorMaleBirthYear"]

            dynasty_prefix = dynasty_id.split("_")[1] if "_" in dynasty_id else dynasty_id
            char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)
            prog_name: str = self.name_loader.load_names(culture, "male")

            progenitor = Character(
                char_id=char_id,
                name=prog_name,
                sex="Male",
                birth_year=birth_year,
                dynasty=dynasty_id,
                culture=culture,
                religion=religion,
                gender_law=gender_law,
                sexuality_distribution=skills_cfg["sexualityDistribution"],
                is_house=is_house,
                generation=1,
                is_progenitor=True,
                birth_order=1,
                numenorean_blood_tier=blood_tier,
            )

            progenitor.assign_skills(skills_cfg["skillProbabilities"])
            progenitor.assign_education(skills_cfg["educationProbabilities"])
            progenitor.assign_personality_traits(skills_cfg["personalityTraits"])

            skill = progenitor.education_skill or "diplomacy"
            childhood_trait = random.choice(
                self.childhood_by_education.get(skill, ["charming", "curious"])
            )
            progenitor.add_event(f"{birth_year + 3}.01.01", f"trait = {childhood_trait}")

            trait_lines = "\n    ".join(f"trait = {t}" for t in progenitor.personality_traits)
            progenitor.add_event(f"{birth_year + 16}.01.01", trait_lines)

            self.all_characters.append(progenitor)
            self.add_character_to_pool(progenitor)
            logger.info(
                "Seeded progenitor %s (%s) for dynasty %s", char_id, prog_name, dynasty_id
            )


    # ------------------------------------------------------------------
    #  Character pool management
    # ------------------------------------------------------------------

    def add_character_to_pool(self, character: Character) -> None:
        """Register a character into the birth-year pool and apply dynasty modifiers."""
        mortality_penalty = character.apply_dynasty_mortality_penalty()
        character.mortality_risk += mortality_penalty
        self.character_pool.setdefault(character.birth_year, []).append(character)

    def remove_from_unmarried_pools(self, character: Character) -> None:
        """Remove a character from the unmarried male or female pool."""
        pool = self.unmarried_males if character.sex == "Male" else self.unmarried_females
        age = character.age
        if age in pool and character in pool[age]:
            pool[age].remove(character)

    def update_unmarried_pools(self, year: int) -> None:
        """Populate the unmarried pools with newly eligible characters."""
        for char in self.all_characters:
            if not (char.alive and not char.married and char.can_marry):
                continue

            age = char.age
            tier = char.numenorean_blood_tier or 0

            if age < self.marriage_min_age + tier * self.numenor_marriage_inc:
                continue

            eff_age = max(0, age - tier * self.numenor_marriage_inc)
            sex_rates: list[float] = self.marriage_rates[char.sex]
            eff_age = min(eff_age, len(sex_rates) - 1)

            if sex_rates[eff_age] > 0 and random.random() < sex_rates[eff_age]:
                pool = self.unmarried_males if char.sex == "Male" else self.unmarried_females
                pool.setdefault(age, []).append(char)

    # ------------------------------------------------------------------
    #  Fertility helpers
    # ------------------------------------------------------------------

    def get_extended_fertility_rate(self, char: Character, sex: str) -> float:
        """
        Return the effective fertility rate for a character, extending the fertile
        window for Numenorean blood tiers by plateauing at peak fertility.
        """
        base: list[float] = self.fer_f if sex == "Female" else self.fer_m
        peak: float = self.peak_f if sex == "Female" else self.peak_m

        age = char.age
        tier = char.numenorean_blood_tier or 0
        extra = 10 * tier
        n = len(base)

        if age < 16:
            return base[age] if age < n else 0.0

        if age <= 16 + extra:
            return peak

        eff = max(0, min(age - extra, n - 1))
        rate = base[eff]
        penalty = max(0.0, 1.0 - tier * 0.025)
        return rate * penalty

    # ------------------------------------------------------------------
    #  Marriage helpers
    # ------------------------------------------------------------------

    def max_age_diff_for(self, character: Character) -> int:
        """Return the maximum allowed marriage age difference for this character."""
        tier = character.numenorean_blood_tier or 0
        return self.marriage_max_age_diff + tier * 5

    def get_num_fertile_dynasty_members(self, character: Character) -> list[Character]:
        """Return alive, fertile characters belonging to the same dynasty."""
        if not character.dynasty:
            return []

        def _is_fertile(c: Character) -> bool:
            if not c.alive:
                return False
            if c.sex == "Male":
                return 16 <= c.age <= 70
            if c.sex == "Female":
                return 16 <= c.age <= 45
            return False

        return [
            c for c in self.all_characters
            if c.dynasty == character.dynasty and _is_fertile(c)
        ]

    def desperation_value(self, character: Character) -> float:
        """Compute the desperation-marriage probability for an unmarried character."""
        age = character.age
        tier = character.numenorean_blood_tier or 0
        eff_age = max(0, min(age - tier * 5, len(self.desperation_rates) - 1))
        base_chance = self.desperation_rates[eff_age]

        living_count = len(self.get_num_fertile_dynasty_members(character))
        modifier = (max(0, 10 - living_count) * 0.20) + 1.0
        return min(1.0, base_chance * modifier)

    def desperation_marriage_check(self, character: Character, year: int) -> bool:
        """Attempt a desperation lowborn marriage; return True if one occurred."""
        min_age = 16 + (character.numenorean_blood_tier or 0) * 5
        if character.age < min_age:
            return False
        if random.random() < self.desperation_value(character):
            self.generate_lowborn_and_marry(character, year)
            return True
        return False

    def generate_lowborn_and_marry(self, character: Character, year: int) -> None:
        """Create a lowborn spouse, register them, and marry them to the character."""
        logger.debug("Lowborn marriage for %s", character.char_id)

        dynasty_prefix = (
            character.dynasty.split("_")[1]
            if character.dynasty and "_" in character.dynasty
            else "lowborn"
        )
        spouse_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)
        spouse_sex = "Male" if character.sex == "Female" else "Female"
        spouse_name: str = self.name_loader.load_names(
            character.culture, spouse_sex.lower()
        )

        spouse = Character(
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
            numenorean_blood_tier=character.numenorean_blood_tier,
        )

        self.add_character_to_pool(spouse)
        self.all_characters.append(spouse)

        skills_cfg = self.config["skills_and_traits"]
        spouse.assign_skills(skills_cfg["skillProbabilities"])
        spouse.assign_education(skills_cfg["educationProbabilities"])
        spouse.assign_personality_traits(skills_cfg["personalityTraits"])

        skill = spouse.education_skill or "diplomacy"
        childhood_trait = random.choice(
            self.childhood_by_education.get(skill, ["charming", "curious"])
        )
        spouse.add_event(
            f"{spouse.birth_year + 3}.{spouse.birth_month:02d}.{spouse.birth_day:02d}",
            f"trait = {childhood_trait}",
        )
        trait_lines = "\n    ".join(f"trait = {t}" for t in spouse.personality_traits)
        spouse.add_event(
            f"{spouse.birth_year + 16}.{spouse.birth_month:02d}.{spouse.birth_day:02d}",
            trait_lines,
        )

        self.marry_characters(character, spouse, year, children_dynasty=character.dynasty)

    def has_dynasty(self, c: Optional[Character]) -> bool:
        """Return True when the character belongs to a named (non-Lowborn) dynasty."""
        return bool(c and c.dynasty and c.dynasty != "Lowborn")

    def sibling_index(self, c: Character) -> int:
        """Return the 0-based birth-order index of c among its parent's children."""
        parent = c.father or c.mother
        if not parent:
            return 0
        ordered = sorted(
            parent.children,
            key=lambda x: (x.birth_year or 0, x.birth_month or 1, x.birth_day or 1),
        )
        try:
            return ordered.index(c)
        except ValueError:
            return len(ordered)

    def dyn_grandparent(self, child: Character) -> Optional[Character]:
        """Return the grandparent (if any) who shares the child's dynasty."""
        gps = [
            gp for gp in (child.father, child.mother)
            if self.has_dynasty(gp) and gp.dynasty == child.dynasty
        ]
        if not gps:
            return None
        if len(gps) == 1:
            return gps[0]
        return min(gps, key=self.sibling_index)

    def elder_of(self, a: Character, b: Character) -> Character:
        """Return whichever character represents the elder dynastic line."""
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

    def are_siblings(self, char1: Character, char2: Character) -> bool:
        """Return True if char1 and char2 share a parent."""
        return char2 in char1.siblings()

    def are_first_cousins(self, char1: Character, char2: Character) -> bool:
        """Return True if char1 and char2 are first cousins."""
        for p1 in (char1.father, char1.mother):
            for p2 in (char2.father, char2.mother):
                if p1 and p2 and self.are_siblings(p1, p2):
                    return True
        return False

    def pick_partner_by_blood_preference(
        self, seeker: Character, candidates: list[Character]
    ) -> Optional[Character]:
        """
        Select one candidate from the list according to blood-tier preference rules.

        A blooded seeker prefers a partner whose tier is closest to their own.
        A non-blooded seeker prefers a non-blooded partner, else the lowest available tier.
        """
        if not candidates:
            return None

        t_seek = seeker.numenorean_blood_tier or 0
        if t_seek > 0:
            blooded = [c for c in candidates if (c.numenorean_blood_tier or 0) > 0]
            if blooded:
                best_dist = min(abs(t_seek - (c.numenorean_blood_tier or 0)) for c in blooded)
                best = [
                    c for c in blooded
                    if abs(t_seek - (c.numenorean_blood_tier or 0)) == best_dist
                ]
                return random.choice(best)
        else:
            non_blood = [c for c in candidates if (c.numenorean_blood_tier or 0) == 0]
            if non_blood:
                return random.choice(non_blood)
            lowest = min(c.numenorean_blood_tier or 0 for c in candidates)
            best = [c for c in candidates if (c.numenorean_blood_tier or 0) == lowest]
            return random.choice(best)

        return random.choice(candidates)

    def marry_characters(
        self,
        char1: Character,
        char2: Character,
        year: int,
        marriage_type: Optional[str] = None,
        children_dynasty: Optional[str] = None,
    ) -> None:
        """Link two characters as spouses and record the marriage event."""
        if char1.char_id == char2.char_id:
            logger.info("Attempted self-marriage for %s. Skipping.", char1.char_id)
            return
        if char1.married or char2.married:
            logger.debug(
                "One character already married: %s, %s. Skipping.",
                char1.char_id,
                char2.char_id,
            )
            return
        if not char1.alive or not char2.alive:
            return

        if not marriage_type:
            if (
                char1.gender_law in ("AGNATIC", "AGNATIC_COGNATIC")
                and char1.sex == "Male"
            ):
                marriage_type = "add_spouse"
                children_dynasty = char1.dynasty
            elif (
                char1.gender_law in ("ENATIC", "ENATIC_COGNATIC")
                and char1.sex == "Female"
            ):
                marriage_type = "add_matrilineal_spouse"
                children_dynasty = char1.dynasty
            else:
                marriage_type = "add_spouse" if char1.sex == "Male" else "add_matrilineal_spouse"
                children_dynasty = char1.dynasty or char2.dynasty

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

    def match_marriages(
        self,
        males: list[Character],
        females: list[Character],
        year: int,
    ) -> None:
        """Attempt to pair unmarried males with unmarried females."""
        dynasty_sizes: dict[str, int] = {
            dyn: 0 for dyn in {c.dynasty for c in self.all_characters if c.dynasty}
        }
        for character in self.all_characters:
            if character.alive and character.dynasty:
                dynasty_sizes[character.dynasty] += 1

        males.sort(
            key=lambda c: (
                dynasty_sizes.get(c.dynasty, 0),
                c.birth_order if c.birth_order is not None else float("inf"),
            )
        )
        females.sort(
            key=lambda c: (
                dynasty_sizes.get(c.dynasty, 0),
                c.birth_order if c.birth_order is not None else float("inf"),
            )
        )

        for male in males:
            if not male.alive or male.married or not male.can_marry:
                continue

            if self.prioritise_lowborn_marriage.get(male.dynasty, False) and random.random() < 0.6:
                self.generate_lowborn_and_marry(male, year)
                continue

            def _female_filter(f: Character, same_dynasty: bool = False) -> bool:
                if not (f.alive and not f.married and f.can_marry):
                    return False
                if same_dynasty:
                    if f.dynasty != male.dynasty:
                        return False
                else:
                    if f.dynasty == male.dynasty and f.dynasty is not None:
                        return False
                if self.are_siblings(male, f):
                    return False
                if not self.allow_cousin_marriage.get(male.dynasty, False) and self.are_first_cousins(male, f):
                    return False
                max_diff = max(self.max_age_diff_for(male), self.max_age_diff_for(f))
                return abs(f.age - male.age) <= max_diff

            available = [f for f in females if _female_filter(f, same_dynasty=False)]
            if available:
                partner = self.pick_partner_by_blood_preference(male, available)
                if partner:
                    self.marry_characters(male, partner, year)
                continue

            if self.desperation_marriage_check(male, year):
                continue

            same_dyn = [f for f in females if _female_filter(f, same_dynasty=True)]
            if same_dyn:
                partner = self.pick_partner_by_blood_preference(male, same_dyn)
                if partner:
                    self.marry_characters(male, partner, year)

    # ------------------------------------------------------------------
    #  Death check
    # ------------------------------------------------------------------

    def character_death_check(self, character: Character) -> bool:
        """
        Return True if the character dies this year based on mortality tables
        and any active negative events.
        """
        tier = character.numenorean_blood_tier or 0
        effective_age = max(0, min(character.age - 20 * tier, 120))

        if character.is_progenitor and effective_age < 50:
            return False

        sex = character.sex
        mortality_rates: list[float] = self.config["life_stages"]["mortalityRates"][sex]

        if effective_age < 1:
            mortality_rate = 0.0
        elif effective_age < len(mortality_rates):
            mortality_rate = mortality_rates[effective_age]
        else:
            mortality_rate = 1.0

        for event in self.config.get("initialization", {}).get("events", []):
            if (
                character.birth_year >= event.get("startYear")
                and character.birth_year <= event.get("endYear")
                and effective_age >= event.get("characterAgeStart")
                and effective_age <= event.get("characterAgeEnd")
            ):
                mortality_rate = min(1.0, mortality_rate * event.get("deathMultiplier", 1))
                character.negativeEventDeathReason = event.get("deathReason")

        roll = random.random()
        if self.prioritise_lowborn_marriage.get(character.dynasty, False):
            roll *= 0.35

        return roll < mortality_rate

    # ------------------------------------------------------------------
    #  Child creation
    # ------------------------------------------------------------------

    def assign_child_name(
        self,
        child_sex: str,
        mother: Character,
        father: Character,
        child_dynasty: Optional[str],
    ) -> str:
        """Assign a name to a new child based on dynasty name-inheritance rules."""
        dynasties: list[dict] = self.config.get("initialization", {}).get("dynasties", [])
        current_dynasty = next(
            (d for d in dynasties if d["dynastyID"] == child_dynasty), None
        )

        if not current_dynasty:
            logger.warning("Dynasty %s not found; assigning random name.", child_dynasty)
            return self.ensure_unique_name(mother, father, child_sex.lower())

        chances = current_dynasty["nameInheritance"]
        chosen = random.choices(
            ["grandparent", "parent", "none"],
            weights=[
                chances["grandparentNameInheritanceChance"],
                chances["parentNameInheritanceChance"],
                chances["noNameInheritanceChance"],
            ],
        )[0]

        if chosen == "grandparent":
            grandparent = (father.father if child_sex == "Male" else mother.mother)
            if grandparent:
                return grandparent.name

        if chosen == "parent":
            return father.name if child_sex == "Male" else mother.name

        return self.ensure_unique_name(mother, father, child_sex.lower())

    def ensure_unique_name(
        self, mother: Character, father: Character, child_gender: str
    ) -> str:
        """Return a unique name from the culture pool, or any random name as fallback."""
        existing = {
            c.name for c in (mother.children + father.children) if c.alive
        }
        available = self.name_loader.get_all_names(mother.culture, child_gender)
        unique = [n for n in available if n not in existing]
        if unique:
            return random.choice(unique)
        if available:
            logger.warning("No unique names available; using duplicate.")
            return random.choice(available)
        fallback = f"Default_{child_gender}"
        logger.error(
            "No names for culture '%s', gender '%s'. Using fallback '%s'.",
            mother.culture,
            child_gender,
            fallback,
        )
        return fallback

    def create_child(
        self, mother: Character, father: Character, birth_year: int
    ) -> Optional[Character]:
        """
        Attempt to create a legitimate child from two married characters.
        Returns None if any constraint (generation cap, spacing, child limit) is violated.
        """
        maximum_children: int = self.config["life_stages"]["maximumNumberOfChildren"]
        if len(mother.children) >= maximum_children:
            return None

        couple_key = (father.char_id, mother.char_id)
        last_birth = self.couple_last_child_year.get(couple_key)
        min_years: int = self.config["life_stages"]["minimumYearsBetweenChildren"]
        if last_birth is not None and birth_year < last_birth + min_years:
            return None

        self.character_count += 1
        child_generation = max(mother.generation, father.generation) + 1
        if child_generation > self.config["initialization"]["generationMax"]:
            return None

        # Determine sex with gender-law bias.
        has_male_sibling = any(s.sex == "Male" for s in mother.children + father.children)
        has_female_sibling = any(s.sex == "Female" for s in mother.children + father.children)

        if father.gender_law in ("AGNATIC", "AGNATIC_COGNATIC") and not has_male_sibling:
            male_chance = 0.9
        elif mother.gender_law in ("ENATIC", "ENATIC_COGNATIC") and not has_female_sibling:
            male_chance = 0.1
        else:
            male_chance = 0.5

        child_sex = "Male" if random.random() < male_chance else "Female"

        # Determine dynasty from the elder parent's line.
        if father.gender_law in ("AGNATIC", "AGNATIC_COGNATIC") and mother.gender_law in ("AGNATIC", "AGNATIC_COGNATIC"):
            child_dynasty = father.dynasty
            child_is_house = father.is_house
            child_culture = father.culture
            child_religion = father.religion
            child_gender_law = father.gender_law
        elif mother.gender_law in ("ENATIC", "ENATIC_COGNATIC") and mother.sex == "Female":
            child_dynasty = mother.dynasty
            child_is_house = mother.is_house
            child_culture = mother.culture
            child_religion = mother.religion
            child_gender_law = mother.gender_law
        else:
            elder = self.elder_of(mother, father)
            child_dynasty = elder.dynasty
            child_is_house = elder.is_house
            child_culture = elder.culture
            child_religion = elder.religion
            child_gender_law = elder.gender_law

        dynasty_prefix = (
            child_dynasty.split("_")[1]
            if child_dynasty and "_" in child_dynasty
            else "lowborn"
        )
        child_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)
        child_name = self.assign_child_name(child_sex, mother, father, child_dynasty)

        birth_order = len(mother.children) + 1
        fertility_modifier = self._compute_fertility_modifier(
            birth_order, father, mother, child_dynasty
        )

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
            sexuality_distribution=self.config["skills_and_traits"]["sexualityDistribution"],
            generation=child_generation,
            birth_order=birth_order,
            fertilityModifier=fertility_modifier,
        )

        init_cfg = self.config.get("initialization", {})
        Character.inherit_numenorean_blood(
            child, father, mother,
            init_cfg.get("numenorInheritance", {}),
            init_cfg.get("numenorDecline", {}),
        )

        child.father = father if father.sex == "Male" else mother
        child.mother = mother if mother.sex == "Female" else father
        mother.children.append(child)
        father.children.append(child)

        child.assign_skills(self.config["skills_and_traits"]["skillProbabilities"])
        child.assign_education(self.config["skills_and_traits"]["educationProbabilities"])
        Character.inherit_congenital(child, father, mother)

        self.couple_last_child_year[couple_key] = birth_year
        return child

    def _compute_fertility_modifier(
        self,
        birth_order: int,
        father: Character,
        mother: Character,
        child_dynasty: Optional[str],
    ) -> float:
        """Derive the fertility modifier for the next child based on birth order and dynasty."""
        order_modifiers = {1: 1.0, 2: 0.80, 3: 0.60, 4: 0.40, 5: 0.20}
        modifier = order_modifiers.get(birth_order, 0.10)

        alive_count = sum(
            1 for c in self.all_characters
            if c.dynasty == child_dynasty and c.alive and 16 <= c.age <= (70 if c.sex == "Male" else 45)
        )

        if alive_count > 8:
            parent = father if father.dynasty == child_dynasty else mother
            if parent.fertilityModifier != 1:
                modifier *= parent.fertilityModifier
        else:
            modifier = 1.0

        if father.dynasty == child_dynasty and self.prioritise_lowborn_marriage.get(father.dynasty, False):
            modifier *= father.fertilityModifier * 0.65
        elif mother.dynasty == child_dynasty and self.prioritise_lowborn_marriage.get(mother.dynasty, False):
            modifier *= mother.fertilityModifier * 0.65

        return modifier

    def create_bastard_child(
        self, parent: Character, birth_year: int, is_male: bool
    ) -> Optional[Character]:
        """Create an illegitimate child for the given parent."""
        maximum_children: int = self.config["life_stages"]["maximumNumberOfChildren"]
        if len(parent.children) >= maximum_children:
            return None

        if parent.sex == "Female":
            age = parent.age
            fer = self.config["life_stages"]["fertilityRates"]["Female"]
            if age >= len(fer) or fer[age] == 0.0:
                return None

        self.character_count += 1
        child_generation = parent.generation + 1
        if child_generation > self.config["initialization"]["generationMax"]:
            return None

        has_male = any(s.sex == "Male" for s in parent.children)
        has_female = any(s.sex == "Female" for s in parent.children)

        if parent.gender_law in ("AGNATIC", "AGNATIC_COGNATIC") and not has_male:
            male_chance = 0.65
        elif parent.gender_law in ("ENATIC", "ENATIC_COGNATIC") and not has_female:
            male_chance = 0.35
        else:
            male_chance = 0.5

        child_sex = "Male" if random.random() < male_chance else "Female"

        dynasty_prefix = (
            parent.dynasty.split("_")[1]
            if parent.dynasty and "_" in parent.dynasty
            else "lowborn"
        )
        child_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)
        child_name = self.assign_child_name(child_sex, parent, parent, parent.dynasty)

        adjusted_birth_year = max(birth_year, parent.birth_year + 16)
        birth_order = len(parent.children) + 1

        child = Character(
            char_id=child_char_id,
            name=child_name,
            sex=child_sex,
            birth_year=adjusted_birth_year,
            dynasty=parent.dynasty,
            is_house=parent.is_house,
            culture=parent.culture,
            religion=parent.religion,
            gender_law=parent.gender_law,
            sexuality_distribution=self.config["skills_and_traits"]["sexualityDistribution"],
            generation=child_generation,
            is_bastard=True,
            birth_order=birth_order,
        )

        init_cfg = self.config.get("initialization", {})
        Character.inherit_numenorean_blood(
            child,
            parent if is_male else None,
            parent if not is_male else None,
            init_cfg.get("numenorInheritance", {}),
            init_cfg.get("numenorDecline", {}),
        )

        if is_male:
            child.father = parent
            child.mother = None
        else:
            child.mother = parent
            child.father = None
        parent.children.append(child)

        child.add_trait("bastard")

        skills_cfg = self.config["skills_and_traits"]
        child.assign_skills(skills_cfg["skillProbabilities"])
        child.assign_education(skills_cfg["educationProbabilities"])
        child.assign_personality_traits(skills_cfg["personalityTraits"])

        skill = child.education_skill or "diplomacy"
        childhood_trait = random.choice(
            self.childhood_by_education.get(skill, ["charming", "curious"])
        )
        child.add_event(
            f"{adjusted_birth_year + 3}.{child.birth_month:02d}.{child.birth_day:02d}",
            f"trait = {childhood_trait}",
        )
        trait_lines = "\n    ".join(f"trait = {t}" for t in child.personality_traits)
        child.add_event(
            f"{adjusted_birth_year + 16}.{child.birth_month:02d}.{child.birth_day:02d}",
            trait_lines,
        )

        return child

    def handle_bastardy(
        self,
        year: int,
        bastardy_chance_male: float,
        bastardy_chance_female: float,
        fertility_rates: dict,
    ) -> None:
        """Generate illegitimate children for eligible characters."""
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

                couple_key = (
                    (character.spouse.char_id, character.char_id)
                    if character.married and character.spouse
                    else None
                )
                if couple_key and self.couple_last_child_year.get(couple_key) == year:
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
    #  Main simulation loop and sub-steps
    # ------------------------------------------------------------------

    def _prepare_simulation_vars(self) -> None:
        """Cache frequently used config values as instance attributes."""
        life = self.config["life_stages"]
        self.desperation_rates = life.get("desperationMarriageRates", [0.0] * 121)
        self.marriage_rates = life["marriageRates"]
        self.fertility_rates = life["fertilityRates"]
        self.bastardy_chance_male: float = life["bastardyChanceMale"]
        self.bastardy_chance_female: float = life["bastardyChanceFemale"]
        self.maximum_children: int = life["maximumNumberOfChildren"]

        fer_f: list[float] = self.fertility_rates["Female"]
        fer_m: list[float] = self.fertility_rates["Male"]
        self.peak_f: float = max(fer_f[16:]) if len(fer_f) > 16 else 0.0
        self.peak_m: float = max(fer_m[16:]) if len(fer_m) > 16 else 0.0
        self.fer_f = fer_f
        self.fer_m = fer_m

    def _backfill_pre_simulation_events(self, min_year: int) -> None:
        """
        Emit age-3 and age-16 trait events for progenitors born before minYear,
        since those years are not visited by the main simulation loop.
        """
        for character in self.all_characters:
            age_at_start = min_year - character.birth_year
            if age_at_start <= 3:
                continue

            has_childhood_event = any(
                detail.strip().startswith("trait =")
                for _, detail in character.events
            )
            if not has_childhood_event:
                skill = character.education_skill or "diplomacy"
                trait = random.choice(
                    self.childhood_by_education.get(skill, ["charming", "curious"])
                )
                character.add_event(
                    f"{character.birth_year + 3}.{character.birth_month:02d}.{character.birth_day:02d}",
                    f"trait = {trait}",
                )

            if age_at_start > 16 and not character.personality_traits:
                character.assign_personality_traits(
                    self.config["skills_and_traits"]["personalityTraits"]
                )
                detail_lines = [f"trait = {t}" for t in character.personality_traits]
                character.add_event(
                    f"{character.birth_year + 16}.{character.birth_month:02d}.{character.birth_day:02d}",
                    "\n    ".join(detail_lines),
                )

    def _process_yearly_updates(self, year: int) -> None:
        """Update character ages and emit age-gated trait events."""
        for character in self.all_characters:
            character.negativeEventDeathReason = None
            if not character.alive:
                continue

            character.age = max(0, year - character.birth_year)

            if character.age == 3:
                skill = character.education_skill or "diplomacy"
                trait = random.choice(
                    self.childhood_by_education.get(skill, ["charming", "curious"])
                )
                character.add_event(
                    f"{year}.{character.birth_month:02d}.{character.birth_day:02d}",
                    f"trait = {trait}",
                )

            if character.age == 16 and not character.personality_traits:
                character.assign_personality_traits(
                    self.config["skills_and_traits"]["personalityTraits"]
                )
                detail_lines = [f"trait = {t}" for t in character.personality_traits]
                character.add_event(
                    f"{year}.{character.birth_month:02d}.{character.birth_day:02d}",
                    "\n    ".join(detail_lines),
                )

    def _process_marriages(self, year: int) -> None:
        """Rebuild marriage pools and match eligible characters.

        Noble-to-noble matching only runs when both male and female pools are
        non-empty.  However, desperation lowborn marriage is attempted for every
        eligible unmarried male regardless of whether noble females are available;
        without this pass, dynasties seeded with only male progenitors would never
        produce marriages or children.
        """
        self.unmarried_males.clear()
        self.unmarried_females.clear()
        self.update_unmarried_pools(year)

        all_males = [m for bucket in self.unmarried_males.values() for m in bucket]
        all_females = [f for bucket in self.unmarried_females.values() for f in bucket]

        if all_males and all_females:
            # Noble-to-noble matching also handles desperation inside match_marriages.
            self.match_marriages(all_males, all_females, year)
        elif all_males:
            # No noble females available: give every eligible male a desperation pass
            # so that dynasties with only male progenitors can still acquire wives.
            for male in all_males:
                if male.alive and not male.married and male.can_marry:
                    self.desperation_marriage_check(male, year)

    def _process_births(self, year: int) -> None:
        """Handle legitimate births and bastardy for the current year."""
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

        self.handle_bastardy(
            year,
            self.bastardy_chance_male,
            self.bastardy_chance_female,
            self.fertility_rates,
        )

    def _process_deaths(self, year: int) -> None:
        """Check for and process character deaths in the current year."""
        for character in self.all_characters:
            if not character.alive:
                continue
            if not self.character_death_check(character):
                continue

            character.alive = False
            death_date = generate_random_date(year)
            character.death_year, character.death_month, character.death_day = (
                int(p) for p in death_date.split(".")
            )
            self.remove_from_unmarried_pools(character)

            tier = character.numenorean_blood_tier or 0
            if character.negativeEventDeathReason is not None:
                death_cause = character.negativeEventDeathReason
            elif character.age > 65 + 20 * tier:
                death_cause = "death_natural_causes"
            elif character.age < 18:
                death_cause = "death_ill"
            elif character.sex == "Male":
                death_cause = random.choice([
                    "death_ill", "death_cancer", "death_battle", "death_attacked",
                    "death_accident", "death_murder", "death_natural_causes",
                    "death_drinking_passive", "death_dungeon_passive",
                ])
            else:
                death_cause = random.choice([
                    "death_ill", "death_cancer", "death_accident", "death_murder",
                ])

            character.add_event(death_date, f"death = {{ death_reason = {death_cause} }}")

            if character.married and character.spouse and character.spouse.alive:
                character.spouse.married = False
                character.spouse.spouse = None

    def _process_survivor_deaths(self, last_sim_year: int) -> None:
        """
        Estimate post-simulation death dates for all characters who survived
        to the end of the main loop by continuing a simplified mortality check.
        """
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

                if not self.character_death_check(character):
                    continue

                character.alive = False
                death_date = generate_random_date(year)
                character.death_year, character.death_month, character.death_day = (
                    int(p) for p in death_date.split(".")
                )

                tier = character.numenorean_blood_tier or 0
                if character.negativeEventDeathReason is not None:
                    death_cause = character.negativeEventDeathReason
                elif character.age > 65 + 20 * tier:
                    death_cause = "death_natural_causes"
                elif character.age < 18:
                    death_cause = "death_ill"
                elif character.sex == "Male":
                    death_cause = random.choice([
                        "death_ill", "death_cancer", "death_battle", "death_attacked",
                        "death_accident", "death_murder", "death_natural_causes",
                        "death_drinking_passive", "death_dungeon_passive",
                    ])
                else:
                    death_cause = random.choice([
                        "death_ill", "death_cancer", "death_accident", "death_murder",
                    ])

                character.add_event(death_date, f"death = {{ death_reason = {death_cause} }}")
                survivors.pop(i)


    # ------------------------------------------------------------------
    #  Dynasty survival enforcement
    # ------------------------------------------------------------------

    def _dynasty_can_continue(self, dynasty_id: str) -> bool:
        """
        Return True when the dynasty has at least one living member who can
        still produce or father children.

        Continuation is assessed by gender law:
          - AGNATIC / AGNATIC_COGNATIC: an unmarried/widowed male aged 16-80.
          - ENATIC / ENATIC_COGNATIC: an unmarried/widowed female aged 16-50.
          - ABSOLUTE_COGNATIC: either sex within their respective fertile windows.
        """
        dynasties_cfg: list[dict] = self.config["initialization"]["dynasties"]
        dynasty_cfg = next(
            (d for d in dynasties_cfg if d["dynastyID"] == dynasty_id), None
        )
        gender_law: str = (dynasty_cfg or {}).get("gender_law", "AGNATIC_COGNATIC")

        living: list[Character] = [
            c for c in self.all_characters
            if c.dynasty == dynasty_id and c.alive
        ]
        if not living:
            return False

        def _can_carry(c: Character) -> bool:
            """Return True when c could still produce or father a legitimate heir.

            For already-married members the spouse must be alive and within her
            own fertile window, otherwise the couple cannot produce children.
            Unmarried members are evaluated on their own fertile window only.
            """
            if not (c.alive and c.can_marry):
                return False

            if c.married:
                spouse = c.spouse
                if not (spouse and spouse.alive):
                    return False
                if c.sex == "Male":
                    return c.age <= 80 and 16 <= spouse.age <= 50
                # Female carrier: her own age determines fertility.
                return 16 <= c.age <= 50

            # Unmarried — check only own fertile window.
            return (
                (c.sex == "Male" and 16 <= c.age <= 80)
                or (c.sex == "Female" and 16 <= c.age <= 50)
            )

        if gender_law in ("AGNATIC", "AGNATIC_COGNATIC"):
            return any(c.sex == "Male" and _can_carry(c) for c in living)
        if gender_law in ("ENATIC", "ENATIC_COGNATIC"):
            return any(c.sex == "Female" and _can_carry(c) for c in living)
        return any(_can_carry(c) for c in living)

    def _emergency_marriage_and_birth(self, dynasty_id: str, year: int) -> bool:
        """
        Guarantee at least one new heir for the dynasty this year.

        Two strategies are attempted in priority order:

        1. Force a birth from an already-married couple where the female is
           still within her fertile window.  This avoids an unnecessary
           lowborn marriage when the dynasty already has a viable couple.
        2. Find the unmarried dynasty member closest to age 25, marry them
           to a generated lowborn spouse, then create a child unconditionally
           (bypassing fertility rolls) so a heir is guaranteed.

        Returns True when a child was created, False when no eligible member
        exists and adoption should be used instead.
        """
        dynasties_cfg: list[dict] = self.config["initialization"]["dynasties"]
        dynasty_cfg = next(
            (d for d in dynasties_cfg if d["dynastyID"] == dynasty_id), None
        )
        gender_law: str = (dynasty_cfg or {}).get("gender_law", "AGNATIC_COGNATIC")

        def _gender_eligible(c: Character) -> bool:
            """Return True when c satisfies the dynasty gender-law fertility check."""
            if gender_law in ("AGNATIC", "AGNATIC_COGNATIC"):
                return c.sex == "Male" and 16 <= c.age <= 80
            if gender_law in ("ENATIC", "ENATIC_COGNATIC"):
                return c.sex == "Female" and 16 <= c.age <= 50
            return 16 <= c.age <= 80  # ABSOLUTE_COGNATIC

        living: list[Character] = [
            c for c in self.all_characters
            if c.dynasty == dynasty_id and c.alive
        ]

        # Strategy 1: existing married couple with a fertile wife.
        for carrier in sorted(living, key=lambda c: abs(c.age - 25)):
            if not (carrier.can_marry and carrier.married and _gender_eligible(carrier)):
                continue
            spouse = carrier.spouse
            if not (spouse and spouse.alive):
                continue
            female = carrier if carrier.sex == "Female" else spouse
            male = carrier if carrier.sex == "Male" else spouse
            if not (16 <= female.age <= 50):
                continue

            child = self.create_child(female, male, year)
            if child:
                self.add_character_to_pool(child)
                self.all_characters.append(child)
                logger.info(
                    "Emergency birth from existing couple: %s (%s) born to %s + %s for dynasty %s.",
                    child.char_id, child.name, male.char_id, female.char_id, dynasty_id,
                )
                return True

        # Strategy 2: unmarried fertile member receives a lowborn spouse.
        unmarried: list[Character] = [
            c for c in living
            if c.can_marry and not c.married and _gender_eligible(c)
        ]
        if not unmarried:
            return False

        carrier = min(unmarried, key=lambda c: abs(c.age - 25))

        logger.warning(
            "Dynasty %s at extinction risk in year %d — forcing emergency marriage for %s (age %d).",
            dynasty_id, year, carrier.char_id, carrier.age,
        )
        self.generate_lowborn_and_marry(carrier, year)

        if not (carrier.married and carrier.spouse):
            return False

        mother = carrier if carrier.sex == "Female" else carrier.spouse
        father = carrier if carrier.sex == "Male" else carrier.spouse

        if not (mother.alive and father.alive):
            return False

        child = self.create_child(mother, father, year)
        if child:
            self.add_character_to_pool(child)
            self.all_characters.append(child)
            logger.info(
                "Emergency birth: %s (%s) born to %s + %s for dynasty %s.",
                child.char_id, child.name, father.char_id, mother.char_id, dynasty_id,
            )
            return True
        return False

    def _adopt_heir(self, dynasty_id: str, year: int) -> bool:
        """
        Create an adopted male child for the dynasty when no emergency marriage
        is possible.

        The adopted character is a young child (0-5 years old at adoption time)
        created with ``is_adopted = True``.  An ``adopted_by`` event is stored in
        their history so ``Character.format_for_export()`` can emit the CK3
        character flag and guardian relationship block.

        The oldest living dynasty member of parenting age (20-60) is recorded as
        the adopter.  If none exists, the child is added as a standalone ward of
        the dynasty.

        Returns True always — adoption is the final fallback and always succeeds.
        """
        adopter: Optional[Character] = next(
            (
                c for c in sorted(self.all_characters, key=lambda x: -x.age)
                if c.dynasty == dynasty_id and c.alive and 20 <= c.age <= 60
            ),
            None,
        )

        dynasty_prefix = dynasty_id.split("_")[1] if "_" in dynasty_id else dynasty_id
        child_char_id = generate_char_id(dynasty_prefix, self.dynasty_char_counters)

        dynasties_cfg: list[dict] = self.config["initialization"]["dynasties"]
        dynasty_cfg = next(
            (d for d in dynasties_cfg if d["dynastyID"] == dynasty_id), None
        )
        culture: str = adopter.culture if adopter else (dynasty_cfg or {}).get("cultureID", "")
        religion: str = adopter.religion if adopter else (dynasty_cfg or {}).get("faithID", "")
        gender_law: str = adopter.gender_law if adopter else (dynasty_cfg or {}).get("gender_law", "AGNATIC_COGNATIC")
        blood_tier: Optional[int] = (
            adopter.numenorean_blood_tier if adopter else (dynasty_cfg or {}).get("numenorBloodTier")
        )
        generation: int = (adopter.generation + 1) if adopter else 2

        birth_year: int = year - random.randint(0, 5)
        child_name: str = self.name_loader.load_names(culture, "male")

        child = Character(
            char_id=child_char_id,
            name=child_name,
            sex="Male",
            birth_year=birth_year,
            dynasty=dynasty_id,
            is_house=(dynasty_cfg or {}).get("isHouse", False),
            culture=culture,
            religion=religion,
            gender_law=gender_law,
            sexuality_distribution=self.config["skills_and_traits"]["sexualityDistribution"],
            generation=generation,
            is_adopted=True,
            birth_order=1,
            numenorean_blood_tier=blood_tier,
        )

        skills_cfg = self.config["skills_and_traits"]
        child.assign_skills(skills_cfg["skillProbabilities"])
        child.assign_education(skills_cfg["educationProbabilities"])
        child.assign_personality_traits(skills_cfg["personalityTraits"])

        skill = child.education_skill or "diplomacy"
        childhood_trait = random.choice(
            self.childhood_by_education.get(skill, ["charming", "curious"])
        )
        child.add_event(
            f"{birth_year + 3}.{child.birth_month:02d}.{child.birth_day:02d}",
            f"trait = {childhood_trait}",
        )
        trait_lines = "\n    ".join(f"trait = {t}" for t in child.personality_traits)
        child.add_event(
            f"{birth_year + 16}.{child.birth_month:02d}.{child.birth_day:02d}",
            trait_lines,
        )

        adopter_id: str = adopter.char_id if adopter else "unknown"
        adoption_date: str = f"{year}.{child.birth_month:02d}.{child.birth_day:02d}"
        child.add_event(adoption_date, f"adopted_by = {adopter_id}")

        if adopter:
            adopter.children.append(child)
            if adopter.sex == "Male":
                child.father = adopter
            else:
                child.mother = adopter

        self.add_character_to_pool(child)
        self.all_characters.append(child)

        logger.info(
            "Dynasty %s: adopted heir %s (%s) in year %d via %s.",
            dynasty_id, child_char_id, child_name, year, adopter_id,
        )
        return True

    def _enforce_dynasty_survival(self, year: int) -> None:
        """
        For every dynasty flagged with ``forceDynastyAlive``, check whether it
        can still continue naturally.  If not, the following protocol runs:

        1. Emergency marriage + guaranteed birth for the most suitable living
           dynasty member.
        2. Adoption of a young male ward as a final fallback when no
           marriageable member exists.

        This method is called at the end of every simulation year, after deaths
        have been processed, so it can respond to extinctions immediately.
        """
        for dynasty_id, forced in self.force_dynasty_alive.items():
            if not forced:
                continue
            if self._dynasty_can_continue(dynasty_id):
                continue

            logger.warning(
                "Dynasty %s cannot continue naturally in year %d — activating survival protocol.",
                dynasty_id, year,
            )

            succeeded = self._emergency_marriage_and_birth(dynasty_id, year)
            if not succeeded:
                logger.info(
                    "Emergency marriage unavailable for %s in %d — falling back to adoption.",
                    dynasty_id, year,
                )
                self._adopt_heir(dynasty_id, year)

    def run_simulation(self) -> None:
        """Execute the full year-by-year simulation loop."""
        self._prepare_simulation_vars()

        min_year: int = self.config["initialization"]["minYear"]
        max_year: int = self.config["initialization"]["maxYear"]

        self._backfill_pre_simulation_events(min_year)

        for year in range(min_year, max_year + 1):
            self._process_yearly_updates(year)
            self._process_marriages(year)
            self._process_births(year)
            self._process_deaths(year)
            self.update_unmarried_pools(year)
            self._enforce_dynasty_survival(year)

        logger.info("Main simulation loop complete. Processing survivors...")
        self._process_survivor_deaths(max_year)

    # ------------------------------------------------------------------
    #  Export
    # ------------------------------------------------------------------

    def export_characters(self, output_filename: str = "family_history.txt") -> None:
        """
        Write all characters to the character history output file, grouped by dynasty.

        Also wires dynasty language rules into the Character class before
        calling format_for_export() on each character.
        """
        language_rules: dict[str, list[tuple[str, int, int]]] = {}
        for dynasty in self.config.get("initialization", {}).get("dynasties", []):
            dynasty_id: str = dynasty.get("dynastyID", "")
            rules: list[tuple[str, int, int]] = []
            for spec in dynasty.get("languages", []):
                parts = spec.split(",")
                if len(parts) == 3:
                    try:
                        rules.append((parts[0].strip(), int(parts[1]), int(parts[2])))
                    except ValueError:
                        pass
            language_rules[dynasty_id] = rules
        Character.DYNASTY_LANGUAGE_RULES = language_rules

        CHARACTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = CHARACTER_OUTPUT_DIR / output_filename

        dynasty_groups: dict[str, list[Character]] = {}
        for character in self.all_characters:
            if not character.dynasty:
                continue
            dynasty = (
                character.spouse.dynasty
                if character.spouse and character.dynasty == "Lowborn" and character.spouse.dynasty != "Lowborn"
                else character.dynasty
            )
            dynasty_groups.setdefault(dynasty, []).append(character)

        exported_count = 0
        with open(output_path, "w", encoding="utf-8") as fh:
            for dynasty, characters in sorted(dynasty_groups.items()):
                fh.write("################\n")
                fh.write(f"### Dynasty {dynasty}\n")
                fh.write("################\n\n")

                def _sort_key(c: Character) -> int:
                    digits = re.sub(r"\D", "", c.char_id)
                    return int(digits) if digits else 0

                for character in sorted(characters, key=_sort_key):
                    fh.write(character.format_for_export())
                    fh.write("\n")
                    exported_count += 1

        logger.info("Character history exported to %s", output_path)
        logger.info("Total characters exported: %d", exported_count)