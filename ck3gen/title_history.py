"""
ck3gen/title_history.py
~~~~~~~~~~~~~~~~~~~~~~~
Parses an exported character history file and builds CK3-compatible title
history blocks showing each dynasty's succession of rulers.

Two public classes are exposed:
  - CharacterLoader   — reads the flat .txt history file
  - TitleHistory      — derives ruler timelines and writes title_history.txt

The local ``TitleCharacter`` (formerly ``Character``) is intentionally
named differently to avoid a collision with ``ck3gen.character.Character``.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from enum import Enum
from pathlib import Path

from ck3gen.paths import CHARACTER_OUTPUT_DIR

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Enums
# ---------------------------------------------------------------------------

class SuccessionType(Enum):
    """Supported succession order types."""
    PRIMOGENITURE = "primogeniture"
    ULTIMOGENITURE = "ultimogeniture"
    SENIORITY = "seniority"


class GenderLaw(Enum):
    """Supported gender restriction laws for succession."""
    AGNATIC = "agnatic"
    AGNATIC_COGNATIC = "agnatic_cognatic"
    ABSOLUTE_COGNATIC = "absolute_cognatic"
    ENATIC = "enatic"
    ENATIC_COGNATIC = "enatic_cognatic"


# ---------------------------------------------------------------------------
#  Data model
# ---------------------------------------------------------------------------

class TitleCharacter:
    """Lightweight character record parsed from the exported history file."""

    def __init__(
        self,
        identifier: str,
        name: str,
        father: str | None,
        mother: str | None,
        dynasty: str,
        female: bool,
        is_bastard: bool,
        birth_year: int | None,
        birth_month: int | None = None,
        birth_day: int | None = None,
        death_year: int | None = None,
        death_month: int | None = None,
        death_day: int | None = None,
    ) -> None:
        self.id = identifier
        self.name = name
        self.father = father
        self.mother = mother
        self.dynasty = dynasty
        self.female = female
        self.is_bastard = is_bastard
        self.birth_year = birth_year
        self.birth_month = birth_month if birth_month is not None else 1
        self.birth_day = birth_day if birth_day is not None else 1
        self.death_year = death_year
        self.death_month = death_month
        self.death_day = death_day
        self.is_progenitor: bool = self._check_if_progenitor(identifier)

    @staticmethod
    def _check_if_progenitor(identifier: str) -> bool:
        """Return True when the ID ends in exactly the digit 1."""
        return bool(re.search(r"(?<!\d)1$", identifier))

    def __repr__(self) -> str:
        return f"<TitleCharacter {self.name} ({self.id})>"


# ---------------------------------------------------------------------------
#  Loader
# ---------------------------------------------------------------------------

class CharacterLoader:
    """Parses a CK3 history .txt file and stores characters by ID and dynasty."""

    def __init__(self) -> None:
        self.characters: dict[str, TitleCharacter] = {}
        self.dynasties: defaultdict[str, list[TitleCharacter]] = defaultdict(list)

    def load_characters(self, filename: str | Path) -> None:
        """Read and parse the character history flat file."""
        with open(filename, encoding="utf-8") as f:
            data = f.read()

        character_blocks = re.findall(
            r"(\w+) = \{\s*((?:[^{}]*|\{(?:[^{}]*|\{[^}]*\})*\})*)\s*\}",
            data,
            re.DOTALL,
        )

        for identifier, content in character_blocks:
            name = self._extract_value(r"name\s*=\s*(\w+)", content)
            father = self._extract_value(r"father\s*=\s*(\w+)", content, default=None)
            mother = self._extract_value(r"mother\s*=\s*(\w+)", content, default=None)
            dynasty = self._extract_value(r"dynasty\s*=\s*(\w+)", content, default="Lowborn")
            female = bool(re.search(r"female\s*=\s*yes", content))
            is_bastard = bool(re.search(r"trait\s*=\s*bastard", content))

            birth_match = re.search(
                r"(\d{4})\.(\d{2})\.(\d{2})\s*=\s*\{\s*birth\s*=\s*yes", content
            )
            death_year = death_month = death_day = None
            for m in re.finditer(
                r"(\d{4})\.(\d{2})\.(\d{2})\s*=\s*\{([^}]*)\}", content, re.DOTALL
            ):
                if re.search(r"\bdeath\b", m.group(4)):
                    death_year = int(m.group(1))
                    death_month = int(m.group(2))
                    death_day = int(m.group(3))
                    break

            character = TitleCharacter(
                identifier=identifier,
                name=name,
                father=father,
                mother=mother,
                dynasty=dynasty,
                female=female,
                is_bastard=is_bastard,
                birth_year=int(birth_match.group(1)) if birth_match else None,
                birth_month=int(birth_match.group(2)) if birth_match else None,
                birth_day=int(birth_match.group(3)) if birth_match else None,
                death_year=death_year,
                death_month=death_month,
                death_day=death_day,
            )
            self.characters[identifier] = character
            self.dynasties[dynasty].append(character)

    @staticmethod
    def _extract_value(pattern: str, content: str, default: str | None = "") -> str | None:
        match = re.search(pattern, content)
        return match.group(1) if match else default

    def print_family_info(self) -> None:
        """Log a debug summary of each non-lowborn character's lineage."""
        for character in self.characters.values():
            if character.dynasty and character.dynasty != "Lowborn":
                logger.debug(
                    "Character %s | Father: %s | Mother: %s | Dynasty: %s | Progenitor: %s",
                    character.id,
                    character.father or "None",
                    character.mother or "None",
                    character.dynasty,
                    character.is_progenitor,
                )


# ---------------------------------------------------------------------------
#  Title history builder
# ---------------------------------------------------------------------------

class TitleHistory:
    """Derives ruler succession timelines from loaded characters and config."""

    def __init__(self, character_loader: CharacterLoader, config_file: str | Path) -> None:
        # dynasty_id -> list of (ruler_id, startY, startM, startD, endY, endM, endD)
        self.titles: dict[str, list[tuple]] = {}
        self.characters = character_loader.characters
        self.dynasties = character_loader.dynasties
        self.config: list[dict] = self._load_json_file(config_file)

        self.parent_to_children: defaultdict[str, list[TitleCharacter]] = defaultdict(list)
        for char_id, char in self.characters.items():
            if char.father in self.characters:
                self.parent_to_children[char.father].append(self.characters[char.father])
            if char.mother in self.characters:
                self.parent_to_children[char.mother].append(self.characters[char.mother])

        # Rebuild correctly — index children, not parents
        self.parent_to_children = defaultdict(list)
        for char in self.characters.values():
            if char.father and char.father in self.characters:
                self.parent_to_children[char.father].append(char)
            if char.mother and char.mother in self.characters:
                self.parent_to_children[char.mother].append(char)

    @staticmethod
    def _load_json_file(filename: str | Path) -> list[dict]:
        """Load the dynasties list from the initialization JSON config."""
        try:
            with open(filename, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("dynasties", [])
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.error("Error loading config file '%s': %s", filename, exc)
            return []

    # ------------------------------------------------------------------
    #  Public entry points
    # ------------------------------------------------------------------

    def build_title_histories(self) -> None:
        """For every dynasty, build a ruler timeline from progenitor to last heir."""
        dynasty_configs = self.parse_config()

        for dynasty_name, (succession_type, gender_law) in dynasty_configs.items():
            if dynasty_name not in self.dynasties:
                continue

            progenitor = self.find_progenitor(dynasty_name)
            if not progenitor:
                continue

            title_line: list[tuple] = []
            current_ruler: TitleCharacter | None = progenitor
            rule_start = self.get_birth_date(current_ruler)

            while current_ruler:
                rule_end = self.get_death_date(current_ruler)

                if rule_end == (9999, 12, 31):
                    title_line.append((current_ruler.id, *rule_start, *rule_end))
                    break

                title_line.append((current_ruler.id, *rule_start, *rule_end))
                next_ruler = self.determine_heir(current_ruler, succession_type, gender_law)
                rule_start = rule_end if next_ruler else None
                current_ruler = next_ruler

            self.titles[dynasty_name] = title_line

    def write_title_histories_to_file(self) -> None:
        """Write placeholder_title blocks to title_history.txt in CK3 format."""
        CHARACTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = CHARACTER_OUTPUT_DIR / "title_history.txt"

        with open(output_path, "w", encoding="utf-8") as file:
            for dynasty, rulers in self.titles.items():
                file.write("placeholder_title = {\n")

                placeholder: dict[str, dict] = {}

                for idx, ruler_data in enumerate(rulers):
                    ruler_id, by, bm, bd, dy, dm, dd = ruler_data
                    date_string = f"{by:04}.{bm:02}.{bd:02}"
                    placeholder[date_string] = {"holder": str(ruler_id)}

                    if idx + 1 < len(rulers):
                        nxt = rulers[idx + 1]
                        next_key = f"{nxt[1]:04}.{nxt[2]:02}.{nxt[3]:02}"
                        placeholder[next_key] = {"holder": f"{nxt[0]}"}

                for date, entry in placeholder.items():
                    file.write(f"    {date} = {{\n")
                    file.write(f"        holder = {entry['holder']}\n")
                    file.write("    }\n")

                file.write("}\n\n")

    # ------------------------------------------------------------------
    #  Config parsing
    # ------------------------------------------------------------------

    def parse_config(self) -> dict[str, tuple[SuccessionType, GenderLaw]]:
        """Build a mapping of dynasty ID → (SuccessionType, GenderLaw) from JSON config."""
        results: dict[str, tuple[SuccessionType, GenderLaw]] = {}
        for entry in self.config:
            name = entry.get("dynastyID")
            if not name:
                continue

            succ_str = entry.get("succession", "PRIMOGENITURE").upper()
            try:
                succession_type = SuccessionType[succ_str]
            except KeyError:
                succession_type = SuccessionType.PRIMOGENITURE

            gl_str = entry.get("gender_law", "AGNATIC_COGNATIC").upper()
            try:
                gender_law = GenderLaw[gl_str]
            except KeyError:
                gender_law = GenderLaw.AGNATIC_COGNATIC

            results[name] = (succession_type, gender_law)
        return results

    # ------------------------------------------------------------------
    #  Heir determination
    # ------------------------------------------------------------------

    def find_progenitor(self, dynasty: str) -> TitleCharacter | None:
        """Return the progenitor character for a dynasty, or None."""
        for person in self.dynasties.get(dynasty, []):
            if person.is_progenitor:
                return person
        return None

    def determine_heir(
        self,
        ruler: TitleCharacter,
        succession_type: SuccessionType,
        gender_law: GenderLaw,
    ) -> TitleCharacter | None:
        """Return the next ruler after the given ruler's death date."""
        parent_death_date = self.get_death_date(ruler)

        if succession_type == SuccessionType.SENIORITY:
            return self.find_heir_seniority(ruler, gender_law, parent_death_date)

        visited: set[str] = set()
        heir = self.find_heir_primoultimo(
            ruler, succession_type, gender_law, parent_death_date, visited, allow_bastards=False
        )
        if heir:
            return heir

        return self.find_heir_primoultimo(
            ruler, succession_type, gender_law, parent_death_date, set(), allow_bastards=True
        )

    def find_heir_seniority(
        self,
        ruler: TitleCharacter,
        gender_law: GenderLaw,
        parent_death_date: tuple[int, int, int],
    ) -> TitleCharacter | None:
        """Return the oldest living valid dynasty member at the time of succession."""
        members = self.dynasties.get(ruler.dynasty, [])
        return (
            self._pick_oldest_living(members, gender_law, parent_death_date, allow_bastards=False)
            or self._pick_oldest_living(members, gender_law, parent_death_date, allow_bastards=True)
        )

    def _pick_oldest_living(
        self,
        members: list[TitleCharacter],
        gender_law: GenderLaw,
        parent_death_date: tuple[int, int, int],
        allow_bastards: bool,
    ) -> TitleCharacter | None:
        """Filter, sort ascending by birth date, and return the first living candidate."""
        valid = [
            c for c in members
            if (allow_bastards or not c.is_bastard)
            and self._is_valid_by_gender_law(c, gender_law)
            and self.get_birth_date(c) <= parent_death_date
        ]
        valid.sort(key=self.get_birth_date)
        for candidate in valid:
            if self._is_alive_at(candidate, parent_death_date):
                return candidate
        return None

    def find_heir_primoultimo(
        self,
        ruler: TitleCharacter | None,
        succession_type: SuccessionType,
        gender_law: GenderLaw,
        parent_death_date: tuple[int, int, int],
        visited: set[str],
        allow_bastards: bool,
    ) -> TitleCharacter | None:
        """Recursively search for the next heir under primogeniture/ultimogeniture."""
        if ruler is None or ruler.id in visited:
            return None
        visited.add(ruler.id)

        children = self.get_children_in_birth_order(ruler.id)
        valid_kids = [
            c for c in children
            if (allow_bastards or not c.is_bastard)
            and self._is_valid_by_gender_law(c, gender_law)
            and self.get_birth_date(c) <= parent_death_date
        ]

        reverse_sort = succession_type == SuccessionType.ULTIMOGENITURE

        if gender_law == GenderLaw.AGNATIC_COGNATIC:
            males = sorted([c for c in valid_kids if not c.female], key=self.get_birth_date, reverse=reverse_sort)
            females = sorted([c for c in valid_kids if c.female], key=self.get_birth_date, reverse=reverse_sort)
            ordered_kids = males + females
        elif gender_law == GenderLaw.ENATIC_COGNATIC:
            females = sorted([c for c in valid_kids if c.female], key=self.get_birth_date, reverse=reverse_sort)
            males = sorted([c for c in valid_kids if not c.female], key=self.get_birth_date, reverse=reverse_sort)
            ordered_kids = females + males
        else:
            ordered_kids = sorted(valid_kids, key=self.get_birth_date, reverse=reverse_sort)

        for child in ordered_kids:
            if self._is_alive_at(child, parent_death_date):
                return child
            heir = self.find_heir_primoultimo(
                child, succession_type, gender_law, parent_death_date, visited, allow_bastards
            )
            if heir:
                return heir

        parent = self._get_relevant_parent(ruler, gender_law)
        if parent:
            if self._is_alive_at(parent, parent_death_date):
                return parent
            return self.find_heir_primoultimo(
                parent, succession_type, gender_law, parent_death_date, visited, allow_bastards
            )

        return None

    # ------------------------------------------------------------------
    #  Validity / date helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid_by_gender_law(character: TitleCharacter, gender_law: GenderLaw) -> bool:
        """Return True if the character's sex satisfies the gender law."""
        if gender_law == GenderLaw.AGNATIC:
            return not character.female
        if gender_law == GenderLaw.ENATIC:
            return character.female
        return True  # ABSOLUTE_COGNATIC, AGNATIC_COGNATIC, ENATIC_COGNATIC all allow both

    def _get_relevant_parent(
        self,
        ruler: TitleCharacter,
        gender_law: GenderLaw,
    ) -> TitleCharacter | None:
        """Return the parent relevant to the gender law (father for agnatic, mother for enatic)."""
        if gender_law in (GenderLaw.ENATIC, GenderLaw.ENATIC_COGNATIC):
            parent_id = ruler.mother
        else:
            parent_id = ruler.father
        return self.characters.get(parent_id) if parent_id and parent_id in self.characters else None

    def _is_alive_at(
        self,
        character: TitleCharacter,
        date_tuple: tuple[int, int, int],
    ) -> bool:
        """Return True if the character was alive on the given date."""
        if character.death_year is None:
            return True
        return self.get_death_date(character) > date_tuple

    def is_alive(self, character: TitleCharacter, current_year: int) -> bool:
        """Return True if the character is alive in the given year."""
        if character.death_year is None:
            return True
        return character.death_year > current_year or (
            character.death_year == current_year and (character.death_month or 12) >= 1
        )

    @staticmethod
    def get_birth_date(person: TitleCharacter) -> tuple[int, int, int]:
        """Return a sortable birth date tuple (year, month, day)."""
        return (person.birth_year or 0, person.birth_month or 1, person.birth_day or 1)

    @staticmethod
    def get_death_date(person: TitleCharacter) -> tuple[int, int, int]:
        """Return a sortable death date tuple, defaulting to (9999, 12, 31) for the living."""
        return (person.death_year or 9999, person.death_month or 12, person.death_day or 31)

    def get_children_in_birth_order(self, parent_id: str) -> list[TitleCharacter]:
        """Return children of a parent sorted by birth date ascending."""
        children = self.parent_to_children.get(parent_id, [])
        return sorted(
            children,
            key=lambda c: (c.birth_year or 0, c.birth_month or 1, c.birth_day or 1),
        )

    def convert_to_ingame_date(self, year: int | str) -> str:
        """Convert a numeric year to an in-game era label (T.A., F.A., or S.A.)."""
        if isinstance(year, str) and not year.isdigit():
            return "?"
        year = int(year)
        if year > 4033:
            return f"T.A. {year - 4033}"
        if 592 < year <= 4033:
            return f"F.A. {year - 592}"
        return f"S.A. {year}"

    def print_title_histories(self) -> None:
        """Log all ruler timelines at DEBUG level."""
        for dynasty, rulers in self.titles.items():
            logger.debug("--- Dynasty: %s ---", dynasty)
            for ruler_id, by, bm, bd, dy, dm, dd in rulers:
                inherited = f"{self.convert_to_ingame_date(by)}.{bm:02}.{bd:02}"
                died = f"{self.convert_to_ingame_date(dy)}.{dm:02}.{dd:02}"
                logger.debug("Ruler: %s | Inherited: %s | Died: %s", ruler_id, inherited, died)