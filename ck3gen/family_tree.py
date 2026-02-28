"""
ck3gen/family_tree.py
~~~~~~~~~~~~~~~~~~~~~
Builds and renders Graphviz family-tree images for each dynasty.

Graph direction is read from ``config["initialization"]["treeGeneration"]``.
Valid values:  LR (Left→Right), RL (Right→Left), TB (Top→Bottom), BT (Bottom→Top).

Usage example:
    tree = FamilyTree("family_history.txt", "title_history.txt", config)
    tree.build_trees()
    tree.render_trees()
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

import graphviz

from ck3gen.paths import CHARACTER_OUTPUT_DIR, TREE_OUTPUT_DIR

logger = logging.getLogger(__name__)


class FamilyTree:
    """Parses character and title history files and renders Graphviz family trees."""

    ROMAN: dict[int, str] = {
        1: "I",   2: "II",   3: "III", 4: "IV",  5: "V",
        6: "VI",  7: "VII",  8: "VIII", 9: "IX",  10: "X",
    }

    def __init__(
        self,
        character_file: str | Path,
        title_file: str | Path,
        config: dict,
    ) -> None:
        self.characters: dict[str, dict] = {}
        self.dynasties: defaultdict[str, list[str]] = defaultdict(list)
        self.title_holders: dict[str, dict] = {}
        self.graphs: dict[str, graphviz.Digraph] = {}
        self.config = config
        self.graphLook: str = config["initialization"]["treeGeneration"]

        self.load_characters(character_file)
        self.load_titles(title_file)

    # ------------------------------------------------------------------
    #  Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_to_ingame_date(year: str | int) -> str:
        """Convert a numeric year to an in-game era label (T.A., F.A., or S.A.)."""
        s = str(year)
        if not s.isdigit():
            return ""
        y = int(s)
        if y > 4033:
            return str(y - 4033)
        if 592 < y <= 4033:
            return str(y - 592)
        return ""

    @staticmethod
    def _extract_value(pattern: str, text: str, default: str | None = "") -> str | None:
        """Return the first capture group of pattern in text, or default."""
        m = re.search(pattern, text)
        return m.group(1) if m else default

    # ------------------------------------------------------------------
    #  File loading
    # ------------------------------------------------------------------

    def load_characters(self, filename: str | Path) -> None:
        """Parse the character history .txt file and populate self.characters."""
        with open(filename, encoding="utf-8") as f:
            data = f.read()

        character_blocks = re.findall(
            r"(\w+) = \{\s*((?:[^{}]*|\{(?:[^{}]*|\{[^}]*\})*\})*)\s*\}",
            data,
            re.DOTALL,
        )

        for identifier, content in character_blocks:
            char_data: dict = {"id": identifier}

            char_data["name"] = self._extract_value(r"name\s*=\s*(\w+)", content)
            char_data["father"] = self._extract_value(r"father\s*=\s*(\w+)", content, default=None)
            char_data["mother"] = self._extract_value(r"mother\s*=\s*(\w+)", content, default=None)
            char_data["dynasty"] = self._extract_value(r"dynasty\s*=\s*(\w+)", content, default="Lowborn")

            char_data["female"] = "yes" if re.search(r"\bfemale\b\s*=\s*yes", content, re.IGNORECASE) else "no"
            char_data["is_bastard"] = bool(re.search(r"\btrait\s*=\s*bastard\b", content, re.IGNORECASE))

            blood_match = re.search(r"\btrait\s*=\s*blood_of_numenor_(\d+)\b", content)
            char_data["numenor_tier"] = int(blood_match.group(1)) if blood_match else None

            birth_match = re.search(
                r"(\d{4})\.\d{2}\.\d{2}\s*=\s*\{\s*birth\s*=\s*yes", content
            )
            char_data["birth_year"] = (
                self._convert_to_ingame_date(birth_match.group(1)) if birth_match else ""
            )

            char_data["death_year"] = ""
            for m in re.finditer(
                r"(\d{4})\.(\d{2})\.(\d{2})\s*=\s*\{([^}]*)\}", content, re.DOTALL
            ):
                if re.search(r"\bdeath\b", m.group(4)):
                    char_data["death_year"] = self._convert_to_ingame_date(m.group(1))
                    break

            self.characters[identifier] = char_data
            self.dynasties[char_data["dynasty"]].append(identifier)

    def load_titles(self, filename: str | Path) -> None:
        """Parse the title history file and track start/end dates for each title holder."""
        try:
            with open(filename, encoding="utf-8") as f:
                data = f.read()
        except FileNotFoundError:
            logger.warning("Title history file '%s' not found. Skipping title processing.", filename)
            return

        title_blocks = re.findall(
            r"(\w+)\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", data, re.DOTALL
        )

        for _title_name, content in title_blocks:
            matches = re.findall(
                r"(\d{4}\.\d{2}\.\d{2})\s*=\s*\{[^}]*\bholder\s*=\s*(\w+)", content
            )

            previous_holder: str | None = None

            for date, holder in matches:
                y, mo, d = date.split(".")
                year, month, day = int(y), int(mo), int(d)

                if previous_holder and previous_holder != holder and previous_holder != "0":
                    self.title_holders[previous_holder]["end_date"] = (
                        f"{year}.{month:02d}.{day:02d}"
                    )

                if holder != "0":
                    if holder not in self.title_holders:
                        self.title_holders[holder] = {
                            "start_date": f"{year}.{month:02d}.{day:02d}",
                            "end_date": None,
                        }
                    else:
                        self.title_holders[holder]["start_date"] = f"{year}.{month:02d}.{day:02d}"

                previous_holder = holder

            if previous_holder and previous_holder != "0":
                if self.title_holders.get(previous_holder, {}).get("end_date") is None:
                    self.title_holders[previous_holder]["end_date"] = "Present"

    # ------------------------------------------------------------------
    #  Tree building
    # ------------------------------------------------------------------

    def build_trees(self) -> None:
        """Generate a Graphviz Digraph for each dynasty and store in self.graphs."""
        for dynasty, members in self.dynasties.items():
            graph = graphviz.Digraph(
                comment=f"{dynasty} Family Tree",
                graph_attr={"rankdir": self.graphLook, "bgcolor": "#A0C878"},
            )

            male_count = sum(1 for cid in members if self.characters[cid].get("female") != "yes")
            female_count = len(members) - male_count
            ruler_count = sum(1 for cid in members if cid in self.title_holders)

            birth_years = [self.characters[cid]["birth_year"] for cid in members if self.characters[cid]["birth_year"]]
            oldest = min(birth_years, default="?")
            youngest = max(birth_years, default="?")

            count_label = (
                f"Total Members: {len(members)}\n"
                f"Males: {male_count}\nFemales: {female_count}\nRulers: {ruler_count}\n"
                f"Span: {oldest} – {youngest}"
            )
            graph.node(
                "dynasty_count",
                label=count_label,
                shape="plaintext",
                width="0",
                height="0",
                style="solid",
                color="transparent",
                fontcolor="black",
            )

            external_nodes: dict[str, str] = {}
            marriages: dict[str, str] = {}

            sorted_members = sorted(
                members, key=lambda cid: self.characters[cid]["birth_year"]
            )

            # Read spouseVisible as a string; the config value is "yes" or "no"
            spouse_visible: str = str(
                self.config.get("initialization", {}).get("spouseVisible", "no")
            )

            for char_id in sorted_members:
                char = self.characters[char_id]

                node_color = "pink" if char_id in self.title_holders else "white"

                birth_date = char["birth_year"]
                death_date = char["death_year"]
                age_suffix = ""
                if birth_date and death_date and birth_date.isdigit() and death_date.isdigit():
                    age_suffix = f" ({int(death_date) - int(birth_date)})"

                start_date = self.title_holders.get(char_id, {}).get("start_date", "N/A")
                end_date = self.title_holders.get(char_id, {}).get("end_date", "N/A")

                start_year = self._convert_to_ingame_date(start_date.split(".")[0]) if start_date != "N/A" else "N/A"
                end_year = self._convert_to_ingame_date(end_date.split(".")[0]) if end_date != "N/A" else "N/A"

                tier = char.get("numenor_tier")
                blood_label = f" ({self.ROMAN.get(tier, str(tier))})" if tier else ""

                ruled_label = (
                    f" Ruled: {start_year} - {end_year}"
                    if start_year and start_year != "N/A" and end_year and end_year != "N/A"
                    else ""
                )

                label = (
                    f'< <b>{char["name"]}</b><br/>'
                    f'{char["id"]}<br/>'
                    f'{birth_date} - {death_date}{age_suffix}{blood_label}<br/>'
                    f'{ruled_label} >'
                )

                border_color = "red" if char.get("female") == "yes" else "blue"
                node_style = "filled"
                if char.get("is_bastard", False):
                    node_style += ", diagonals"

                graph.node(
                    char["id"],
                    label=label,
                    style=node_style,
                    fillcolor=node_color,
                    color=border_color,
                    penwidth="5",
                )

                spouse_id = char.get("spouse")
                if spouse_id:
                    marriages[char_id] = spouse_id
                    marriages[spouse_id] = char_id

                for parent_type in ("father", "mother"):
                    parent_id = char.get(parent_type)
                    if not parent_id or parent_id not in self.characters:
                        continue

                    parent_dynasty = self.characters[parent_id]["dynasty"]
                    if parent_dynasty == dynasty:
                        graph.edge(parent_id, char_id)
                    elif spouse_visible == "yes":
                        external_node_id = f"external_{parent_id}"
                        if external_node_id not in external_nodes:
                            p = self.characters[parent_id]
                            external_label = (
                                f'< <b>{p["name"]}</b><br/>'
                                f'{p["birth_year"]} - {p["death_year"]} >'
                            )
                            graph.node(
                                external_node_id,
                                label=external_label,
                                shape="ellipse",
                                style="dashed",
                            )
                            external_nodes[external_node_id] = external_label

                        graph.edge(external_node_id, char_id, style="dashed")

                        ext_spouse = self.characters.get(parent_id, {}).get("spouse")
                        if ext_spouse and ext_spouse in self.characters:
                            graph.edge(external_node_id, ext_spouse, style="bold", penwidth="3", color="black")

            for spouse1, spouse2 in marriages.items():
                if spouse1 in self.characters and spouse2 in self.characters:
                    graph.edge(spouse1, spouse2, style="bold", penwidth="3", color="black")
                    with graph.subgraph() as s:
                        s.attr(rankdir=self.graphLook, rank="same")
                        s.node(spouse1)
                        s.node(spouse2)
                        s.edge(spouse1, spouse2, style="bold", penwidth="3", color="black")

            self.graphs[dynasty] = graph

    def render_trees(self) -> None:
        """Render each dynasty graph to a PNG file in TREE_OUTPUT_DIR."""
        TREE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        for dynasty, graph in self.graphs.items():
            output_path = TREE_OUTPUT_DIR / f"family_tree_{dynasty}"
            graph.render(str(output_path), format="png", cleanup=True)
            logger.info("Family tree for '%s' saved as %s.png", dynasty, output_path)