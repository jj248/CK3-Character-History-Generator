"""
ck3gen/character.py
~~~~~~~~~~~~~~~~~~~
Defines the Character class and supporting congenital-trait helpers used
throughout the CK3 Character History Generator simulation.

DYNASTY_LANGUAGE_RULES is a class-level attribute that must be populated
before export by calling:
    Character.DYNASTY_LANGUAGE_RULES = config_loader.dynasty_language_rules
"""

from __future__ import annotations

import logging
import random
from typing import ClassVar

from utils.utils import generate_random_date

logger = logging.getLogger(__name__)

# ==============================================================
# Congenital-trait helpers (beauty / intellect / physique)
# ==============================================================

_CONGENITAL_TIERS: dict[str, list[str]] = {
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

# Random mutation odds indexed to match each tier entry (bad_3 … good_3)
_RANDOM_PICK_CHANCE: list[float] = [0.0015, 0.0025, 0.005, 0.005, 0.0025, 0.0015]


def _tier_index(trait: str, category: str) -> int | None:
    """Return the tier index (0–5) for a trait in a category, or None."""
    try:
        return _CONGENITAL_TIERS[category].index(trait)
    except ValueError:
        return None


def _parent_trait_idx(parent: Character, category: str) -> int | None:
    """Return the tier index of the parent's trait for a given category, or None."""
    for t in parent.congenital_traits.values():
        idx = _tier_index(t, category)
        if idx is not None:
            return idx
    return None


class Character:
    """Represents a single simulated character and their life history."""

    # Populated once from ConfigLoader before any export runs.
    DYNASTY_LANGUAGE_RULES: ClassVar[dict[str, list[tuple[str, int, int]]]] = {}

    def __init__(
        self,
        char_id: str,
        name: str,
        sex: str,
        birth_year: int,
        dynasty: str | None,
        culture: str,
        religion: str,
        gender_law: str,
        sexuality_distribution: dict[str, float],
        is_house: bool = False,
        generation: int = 1,
        is_progenitor: bool = False,
        is_bastard: bool = False,
        birth_order: int = 1,
        negativeEventDeathReason: str | None = None,
        fertilityModifier: float = 1.0,
        numenorean_blood_tier: int | None = None,
    ) -> None:
        self.is_bastard = is_bastard
        self.char_id = char_id
        self.name = name
        self.sex = sex
        self.birth_year = birth_year
        self.birth_month: int = 1
        self.birth_day: int = 1
        self.age: int = 0  # Updated annually by the simulation loop
        self.death_year: int | None = None
        self.death_month: int | None = None
        self.death_day: int | None = None
        self.alive: bool = True
        self.married: bool = False
        self.spouse: Character | None = None
        self.children: list[Character] = []

        self.dynasty: str = dynasty if dynasty else "Lowborn"

        # Validate gender_law; fall back to a safe default if unrecognised.
        _valid_laws = {"AGNATIC", "AGNATIC_COGNATIC", "ABSOLUTE_COGNATIC", "ENATIC_COGNATIC", "ENATIC"}
        self.gender_law: str = gender_law if gender_law in _valid_laws else "AGNATIC_COGNATIC"

        self.culture = culture
        self.religion = religion
        self.generation = generation
        self.is_progenitor = is_progenitor
        self.is_house = is_house
        self.events: list[tuple[str, str]] = []
        self.father: Character | None = None
        self.mother: Character | None = None
        self.skills: dict[str, int] = {}
        self.education_skill: str | None = None
        self.education_tier: int | None = None
        self.traits: list[str] = []
        self.personality_traits: list[str] = []
        self.congenital_traits: dict[str, str] = {}
        self.sexuality: str | None = None
        self.can_marry: bool = True
        self.assign_sexuality(sexuality_distribution)
        self.mortality_risk: float = 0.0
        self.negativeEventDeathReason: str | None = negativeEventDeathReason
        self.fertilityModifier: float = fertilityModifier
        self.numenorean_blood_tier: int | None = numenorean_blood_tier
        self.birth_order: int = birth_order
        self.marriage_year: int | None = None

        # Record the birth event with a random date inside the birth year.
        birth_date_str = generate_random_date(self.birth_year)
        self.birth_year, self.birth_month, self.birth_day = map(int, birth_date_str.split("."))
        self.add_event(birth_date_str, "birth = yes")

    # ------------------------------------------------------------------
    #  Mortality / fertility helpers
    # ------------------------------------------------------------------

    def apply_dynasty_mortality_penalty(self) -> float:
        """Return an additional mortality multiplier for distant-generation branches."""
        if self.generation >= 4:
            return 0.2 * (self.generation - 3)
        return 0.0

    def fertility_mult(self) -> float:
        """Return a fertility multiplier derived from congenital traits."""
        if "infertile" in self.congenital_traits.values():
            return 0.0
        mult = 1.0 * self.fertilityModifier
        if "fecund" in self.congenital_traits.values():
            mult *= 2.0
        return mult

    # ------------------------------------------------------------------
    #  Family helpers
    # ------------------------------------------------------------------

    def siblings(self) -> list[Character]:
        """Return a list of all half- and full siblings."""
        sibs: set[Character] = set()
        if self.father:
            sibs.update(self.father.children)
        if self.mother:
            sibs.update(self.mother.children)
        sibs.discard(self)
        return list(sibs)

    # ------------------------------------------------------------------
    #  Trait / event assignment
    # ------------------------------------------------------------------

    def add_trait(self, trait: str) -> None:
        """Add a trait to the character if not already present."""
        if trait not in self.traits:
            self.traits.append(trait)

    def add_event(self, event_date: str, event_detail: str) -> None:
        """Append a dated event to the character's history."""
        self.events.append((event_date, event_detail))

    def assign_sexuality(self, sexuality_distribution: dict[str, float]) -> None:
        """Assign sexuality from a weighted distribution and set marry eligibility."""
        sexualities = list(sexuality_distribution.keys())
        probabilities = list(sexuality_distribution.values())
        self.sexuality = random.choices(sexualities, probabilities)[0]
        self.can_marry = self.sexuality == "heterosexual"

    def assign_skills(self, skill_probabilities: dict[str, dict[str, float]]) -> None:
        """Assign all six attributes from weighted probability tables."""
        attributes = ["diplomacy", "martial", "stewardship", "intrigue", "learning", "prowess"]
        for attribute in attributes:
            self.skills[attribute] = self._random_skill_level(attribute, skill_probabilities)

    def _random_skill_level(self, skill_name: str, skill_probabilities: dict[str, dict[str, float]]) -> int:
        """Return a randomly selected level for one skill."""
        skill_probs = skill_probabilities.get(skill_name, {})
        if not skill_probs:
            logger.warning("No skill probabilities defined for %s. Assigning level 0.", skill_name)
            return 0
        levels = [int(k) for k in skill_probs.keys()]
        probabilities = list(skill_probs.values())
        return random.choices(levels, probabilities)[0]

    def assign_education(
        self,
        education_probabilities: dict[str, dict[str, float]],
        weight_exponent: int = 2,
    ) -> None:
        """Assign an education skill and tier, weighted by the character's skill levels."""
        if not self.skills:
            logger.warning("Skills not assigned for %s. Cannot assign education.", self.char_id)
            return

        skills = list(self.skills.keys())
        transformed_weights = [level ** weight_exponent for level in self.skills.values()]

        selected_skill = random.choices(skills, weights=transformed_weights, k=1)[0]
        logger.debug("Character %s selected education skill: %s.", self.char_id, selected_skill)

        self.education_skill = selected_skill
        self.education_tier = self._random_education_level(selected_skill, education_probabilities)

    def _random_education_level(
        self,
        skill_name: str,
        education_probabilities: dict[str, dict[str, float]],
    ) -> int:
        """Return a randomly selected education tier for one skill."""
        edu_probs = education_probabilities.get(skill_name, {})
        if not edu_probs:
            logger.warning("No education probabilities defined for %s. Assigning level 0.", skill_name)
            return 0
        levels = [int(k) for k in edu_probs.keys()]
        probabilities = list(edu_probs.values())
        return random.choices(levels, probabilities)[0]

    def assign_personality_traits(self, personality_traits_config: dict) -> None:
        """Assign personality traits using weighted selection with mutual exclusions."""
        total_traits: int = personality_traits_config.get("totalTraitsPerCharacter", 3)
        available_traits = {k: v for k, v in personality_traits_config.items() if k != "totalTraitsPerCharacter"}

        trait_pool = list(available_traits.keys())
        trait_weights = [available_traits[t]["weight"] for t in trait_pool]

        self.personality_traits = []

        while len(self.personality_traits) < total_traits and trait_pool:
            selected = random.choices(trait_pool, weights=trait_weights, k=1)[0]
            self.personality_traits.append(selected)

            excludes = available_traits[selected].get("excludes", [])
            trait_pool = [t for t in trait_pool if t != selected and t not in excludes]
            trait_weights = [available_traits[t]["weight"] for t in trait_pool]

    # ------------------------------------------------------------------
    #  Congenital-trait inheritance (tiered + single)
    # ------------------------------------------------------------------

    @staticmethod
    def inherit_congenital(
        child: Character,
        father: Character,
        mother: Character,
    ) -> None:
        """
        Populate child.congenital_traits from parent traits and random mutation.

        Handles tiered categories (beauty, intellect, physique) and
        single-tier defects (dwarf, giant, etc.).
        """
        # Tiered categories
        for category, tiers in _CONGENITAL_TIERS.items():
            idx_f = _parent_trait_idx(father, category)
            idx_m = _parent_trait_idx(mother, category)

            best_parent_idx: int | None = None
            if idx_f is not None or idx_m is not None:
                best_parent_idx = max(idx for idx in (idx_f, idx_m) if idx is not None)

            if best_parent_idx is None:
                idx_sequence: range = range(0)  # No parent trait; skip to mutation
            elif best_parent_idx <= 2:
                idx_sequence = range(best_parent_idx, 3)
            else:
                idx_sequence = range(best_parent_idx, -1, -1)

            inherited = False
            for idx in idx_sequence:
                father_has = idx_f == idx
                mother_has = idx_m == idx

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
                else:
                    chance = 0.10

                if random.random() < chance:
                    child.congenital_traits[category] = tiers[idx]
                    inherited = True
                    break

                if (
                    idx == 3
                    and best_parent_idx is not None
                    and best_parent_idx >= 3
                    and (idx_f is None or idx_f > 2)
                    and (idx_m is None or idx_m > 2)
                ):
                    break

            if not inherited:
                rnd = random.random()
                cumulative = 0.0
                for idx, prob in enumerate(_RANDOM_PICK_CHANCE):
                    cumulative += prob
                    if rnd < cumulative:
                        child.congenital_traits[category] = tiers[idx]
                        break

        # Single-tier congenital traits
        SINGLE_TRAITS: list[str] = [
            "clubfooted", "hunchbacked", "lisping", "stuttering",
            "dwarf", "giant", "spindly", "scaly", "albino",
            "wheezing", "bleeder", "fecund", "infertile",
        ]
        MUTEX_GROUPS: list[set[str]] = [
            {"dwarf", "giant"},
            {"fecund", "infertile"},
        ]

        def _conflicts(t: str) -> bool:
            return any(t in grp and grp & set(child.congenital_traits.values()) for grp in MUTEX_GROUPS)

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

            if not inherited and random.random() < 0.005:
                if not _conflicts(trait):
                    child.congenital_traits[trait] = trait

    # ------------------------------------------------------------------
    #  Numenorean blood inheritance
    # ------------------------------------------------------------------

    @staticmethod
    def inherit_numenorean_blood(
        child: Character,
        father: Character | None,
        mother: Character | None,
        params: dict,
        decline_table: dict,
    ) -> None:
        """
        Set child.numenorean_blood_tier based on parent tiers, inheritance
        probability params, and the year-based decline table.
        """
        tf = father.numenorean_blood_tier if father and father.numenorean_blood_tier else 0
        tm = mother.numenorean_blood_tier if mother and mother.numenorean_blood_tier else 0

        if tf == 0 and tm == 0:
            return

        high, low = max(tf, tm), min(tf, tm)
        diff = high - low

        if diff == 0:
            chance = params["sameTierChance"]
            drop = 1
        elif diff <= 2:
            chance = params["closeTierChance"]
            drop = 1
        else:
            chance = params["farTierChance"]
            drop = 2

        if random.random() < chance:
            child.numenorean_blood_tier = high
        else:
            child.numenorean_blood_tier = max(high - drop, 0)

        raw = child.numenorean_blood_tier
        allowed = raw

        for tier_str, cutoff in sorted(decline_table.items(), key=lambda kv: int(kv[0])):
            tier_i = int(tier_str)
            if raw >= tier_i and child.birth_year > cutoff:
                allowed = min(allowed, tier_i - 1)

        child.numenorean_blood_tier = max(allowed, 0)

    # ------------------------------------------------------------------
    #  CK3 export
    # ------------------------------------------------------------------

    def format_for_export(self) -> str:
        """Serialise the character's data and event history to CK3 format."""
        lines: list[str] = [f"{self.char_id} = {{"]
        lines.append(f"\tname = {self.name}")
        if self.sex == "Female":
            lines.append("\tfemale = yes")

        lines.append(f"\tculture = {self.culture}")
        lines.append(f"\treligion = {self.religion}")

        sections: list[str] = []
        if self.dynasty and self.dynasty != "Lowborn":
            key = "dynasty_house" if self.is_house else "dynasty"
            sections.append(f"\t{key} = {self.dynasty}")
        if self.father:
            sections.append(f"\tfather = {self.father.char_id}")
        if self.mother:
            sections.append(f"\tmother = {self.mother.char_id}")
        if sections:
            lines.append("")
            lines.extend(sections)

        lines.append("")
        lines.append(f"\tsexuality = {self.sexuality}")

        if self.skills:
            lines.append("")
            for skill, value in self.skills.items():
                lines.append(f"\t{skill} = {value}")

        # Childhood traits must appear outside event blocks in the CK3 format.
        child_traits: set[str] = {"charming", "curious", "rowdy", "bossy", "pensive"}
        extracted_child_traits: list[str] = []

        if self.traits:
            lines.append("")
            for trait in self.traits:
                lines.append(f"\ttrait = {trait}")

        if self.education_tier is not None or self.congenital_traits:
            lines.append("")

        if self.education_tier is not None and self.education_skill is not None:
            if self.education_skill == "prowess":
                lines.append(f"\ttrait = education_martial_{self.education_tier}")
            else:
                lines.append(f"\ttrait = education_{self.education_skill}_{self.education_tier}")

        for trait in self.congenital_traits.values():
            lines.append(f"\ttrait = {trait}")

        if self.numenorean_blood_tier and 1 <= self.numenorean_blood_tier <= 10:
            lines.append(f"\ttrait = blood_of_numenor_{self.numenorean_blood_tier}")

        # Process and sort all events
        if self.events:
            lines.append("")
            sorted_events = sorted(self.events, key=lambda e: e[0])
            processed_events: list[tuple[str, list[str]]] = []

            for event_date, event_detail in sorted_events:
                try:
                    event_year, event_month, event_day = map(int, event_date.split("."))
                except ValueError:
                    logger.warning(
                        "Invalid event date format for character %s: %s",
                        self.char_id,
                        event_date,
                    )
                    event_year = self.birth_year
                    event_month = self.birth_month
                    event_day = self.birth_day

                age = event_year - self.birth_year
                if (event_month, event_day) < (self.birth_month, self.birth_day):
                    age -= 1

                # Separate childhood traits from the event stream
                if event_detail.strip().startswith("trait ="):
                    lines_in_event = event_detail.strip().splitlines()
                    trait_lines = [l.strip() for l in lines_in_event if l.strip().startswith("trait =")]
                    non_child_trait_lines: list[str] = []
                    for trait_line in trait_lines:
                        trait_name = trait_line.split("=", 1)[1].strip()
                        if trait_name in child_traits:
                            if age < 16:
                                extracted_child_traits.append(trait_name)
                        else:
                            non_child_trait_lines.append(trait_line)

                    if not non_child_trait_lines:
                        continue

                    event_detail = "\n".join(non_child_trait_lines)

                event_lines: list[str] = []
                if event_detail == "birth = yes":
                    event_lines.append(f"\t{event_date} = {{")
                    event_lines.append(f"\t    {event_detail}")

                    lang_effects: list[str] = [
                        lang
                        for lang, start, end in self.DYNASTY_LANGUAGE_RULES.get(self.dynasty, [])
                        if start <= self.birth_year <= end
                    ]
                    if lang_effects:
                        event_lines.append("\t    effect = {")
                        for lang in lang_effects:
                            event_lines.append(f"\t        learn_language = {lang}")
                        event_lines.append("\t    }")
                    event_lines.append("\t}")
                else:
                    if event_detail.startswith("add_spouse") or event_detail.startswith("add_matrilineal_spouse"):
                        event_desc = f"# Married at age {age}"
                    elif event_detail.startswith("trait"):
                        event_desc = ""
                    elif event_detail.startswith("death"):
                        event_desc = f"# Died at age {age}"
                    else:
                        event_desc = f"# Event at age {age}"

                    event_lines.append(f"\t{event_date} = {{  {event_desc}")
                    for detail_line in event_detail.strip().splitlines():
                        event_lines.append(f"\t    {detail_line.strip()}")
                    event_lines.append("\t}")

                processed_events.append((event_date, event_lines))

            # Childhood traits are written as plain trait lines, not inside date blocks.
            for trait in extracted_child_traits:
                lines.append(f"\ttrait = {trait}")

            for _, event_lines in sorted(processed_events, key=lambda e: e[0]):
                lines.extend(event_lines)

        lines.append("}\n")
        return "\n".join(lines)