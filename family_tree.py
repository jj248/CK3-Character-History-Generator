import re
import graphviz
from collections import defaultdict
from config_loader import ConfigLoader

#########################################################
#   For the graph direction, valid arguments are:       #
#   LR - Left->Right                                    #
#   RL - Right->Left                                    #
#   TB - Top->Bottom                                    #
#   BT - Bottom->Top                                    #
#   Both - Will generate LR and TB both                 #
#########################################################


class FamilyTree:
    def __init__(self, character_file, title_file, config):
        self.characters = {}
        self.dynasties = defaultdict(list)  # Stores characters by dynasty
        self.title_holders = set()  # Store characters who inherited the title
        self.load_characters(character_file)
        self.load_titles(title_file)
        self.graphs = {}  # Stores Graphviz objects for each dynasty
        self.config = config
        self.graphLook = self.config['initialization']['treeGeneration']

    def load_characters(self, filename):
        """Parse the .txt file to extract character details."""
        with open(filename, "r", encoding="utf-8") as f:  # Ensure UTF-8 encoding
            data = f.read()

        def convert_to_ingame_date(year):
            """Convert the year into T.A. or S.A. format."""
            if year.isdigit():  # Ensure it's a valid number
                year = int(year)
                if year > 4033:
                    return f"{year - 4033}"
                elif 592 < year <= 4033:
                    return f"{year - 592}"
            return ""  # Default if invalid

        # Regex to find each character block
        character_blocks = re.findall(r"(\w+) = \{\s*((?:[^{}]*|\{(?:[^{}]*|\{[^}]*\})*\})*)\s*\}", data, re.DOTALL)

        for identifier, content in character_blocks:
            char_data = {"id": identifier}

            # Extracting values
            char_data["name"] = self.extract_value(r"name\s*=\s*(\w+)", content)
            char_data["father"] = self.extract_value(r"father\s*=\s*(\w+)", content, default=None)
            char_data["mother"] = self.extract_value(r"mother\s*=\s*(\w+)", content, default=None)
            char_data["dynasty"] = self.extract_value(r"dynasty\s*=\s*(\w+)", content, default="Lowborn")

            # Ensure "is_female" is detected correctly
            is_female_match = re.search(r"\bfemale\b\s*=\s*yes", content, re.IGNORECASE)
            char_data["female"] = "yes" if is_female_match else "no"  # Default to male if absent

            # Check for bastard trait
            is_bastard_match = re.search(r"\btrait\s*=\s*bastard\b", content, re.IGNORECASE)
            char_data["is_bastard"] = True if is_bastard_match else False  # Flag for bastard trait

            # Debugging output
            # print(f"Is Female: {is_female_match}, Is Bastard: {char_data['is_bastard']}")

            # Extract birth and death years
            birth_match = re.search(r"(\d{4})\.\d{2}\.\d{2}\s*=\s*\{\s*birth\s*=\s*yes", content)
            death_match = re.search(r"(\d{4})\.\d{2}\.\d{2}\s*=\s*\{\s*death", content, re.DOTALL)

            char_data["birth_year"] = convert_to_ingame_date(birth_match.group(1)) if birth_match else ""
            char_data["death_year"] = convert_to_ingame_date(death_match.group(1)) if death_match else ""

            # Store character data
            self.characters[identifier] = char_data
            self.dynasties[char_data["dynasty"]].append(identifier)  # Group by dynasty

        # Debugging Output: Ensure Characters Are Loaded
        # print("Characters Loaded:", list(self.characters.keys()))  # <-- Debugging line

    def load_titles(self, filename):
        """Parse title history to find characters who held a title."""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = f.read()
        except FileNotFoundError:
            print(f"Warning: {filename} not found. Skipping title processing.")
            return

        title_blocks = re.findall(r"(\w+)\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", data, re.DOTALL)

        for title_name, content in title_blocks:
            matches = re.findall(r"(\d{4}\.\d{2}\.\d{2})\s*=\s*\{[^}]*\bholder\s*=\s*(\w+)", content)
            for date, holder in matches:
                # print(f"Found title holder in history: {holder}")  # <-- Debug print

                if holder != "0":  # Ignore cases where no one inherits
                    if holder in self.characters:
                        self.title_holders.add(holder)
                    else:
                        print(f"Warning: Holder {holder} from title history not found in character file.")

        # print("Title Holders Identified:", self.title_holders)  # <-- Final check

    def extract_value(self, pattern, text, default=""):
        """Helper function to extract values from a text block."""
        match = re.search(pattern, text)
        return match.group(1) if match else default

    def build_trees(self):
        """Generate a family tree visualization for each dynasty."""
        for dynasty, members in self.dynasties.items():
            graph = graphviz.Digraph(comment=f"{dynasty} Family Tree", graph_attr={"rankdir": self.graphLook})

            # Keep track of external parent nodes and marriages
            external_nodes = {}
            marriages = {}  # Dictionary to store marriage relationships (spouse1 -> spouse2)

            # Sort characters by birth year to ensure eldest is at the top
            sorted_members = sorted(members, key=lambda char_id: self.characters[char_id]["birth_year"])

            for char_id in sorted_members:
                char = self.characters[char_id]
                
                # Check if the character inherited a title
                node_color = "pink" if char_id in self.title_holders else "white"

                label = f'< <b>{char["name"]}</b><br/>{char["id"]}<br/>{char["birth_year"]} - {char["death_year"]} >'
                border_color = "blue"  # Default for males
                if char.get("female") == "yes":
                    border_color = "red"  # Assign red for females

                # Check if the character is a bastard and add a diagonal mark
                node_style = "filled"
                fillcolor = node_color
                penwidth = "2"
                diagonal_mark = ""

                if char.get("is_bastard", False):  # Check if the character is a bastard
                    diagonal_mark = 'diagonal line from top-left to bottom-right'
                    # To represent the mark, we'll use a "diagonal line" as an additional part of the node
                    node_style += ", diagonals"  # We use a custom style to simulate diagonal lines


                # Create the node with a large enough diagonal mark for bastards
                graph.node(char["id"], label=label, style=node_style, fillcolor=fillcolor, color=border_color, penwidth=penwidth)

                # Check for a spouse (marriage detection)
                spouse_id = self.characters.get(char_id, {}).get("spouse")  # Assuming 'spouse' field exists
                if spouse_id:
                    marriages[char_id] = spouse_id
                    marriages[spouse_id] = char_id  # Ensure bidirectional marriage

                # Draw edges for parents
                for parent_type in ["father", "mother"]:
                    parent_id = char.get(parent_type)
                    if parent_id in self.characters:
                        parent_dynasty = self.characters[parent_id]["dynasty"]

                        # If parent is in the same dynasty, link directly
                        if parent_dynasty == dynasty:
                            graph.edge(parent_id, char_id)

                        # Else, check if we should show external parents
                        elif self.config.get('initialization', {}).get('spouseVisible', []) == "yes":
                            external_node_id = f"external_{parent_id}"
                            if external_node_id not in external_nodes:
                                external_label = (
                                    f'< <b>{self.characters[parent_id]["name"]}</b><br/>'
                                    f'{self.characters[parent_id]["birth_year"]} - '
                                    f'{self.characters[parent_id]["death_year"]} >'
                                )
                                graph.node(external_node_id, label=external_label,
                                        shape="ellipse", style="dashed")
                                external_nodes[external_node_id] = external_label

                            # Draw dashed edge from external parent to child
                            graph.edge(external_node_id, char_id, style="dashed")

                            # Check for spouse of external parent and draw a thick line if exists
                            spouse_id = self.characters.get(parent_id, {}).get("spouse")
                            if spouse_id and spouse_id in self.characters:
                                graph.edge(external_node_id, spouse_id,
                                        style="bold", penwidth="3", color="black")

            # Draw marriage lines with bold, thick edges
            for spouse1, spouse2 in marriages.items():
                if spouse1 in self.characters and spouse2 in self.characters:
                    # Connect spouses with a bold line
                    graph.edge(spouse1, spouse2, style="bold", penwidth="3", color="black")

                    # Use a subgraph to position spouses next to each other
                    with graph.subgraph() as s:
                        s.attr(rankdir=self.graphLook, rank='same')
                        s.node(spouse1)
                        s.node(spouse2)
                        s.edge(spouse1, spouse2, style="bold", penwidth="3", color="black")

            self.graphs[dynasty] = graph  # Store graph for later rendering



    def render_trees(self):
        """Render the family trees to files."""
        for dynasty, graph in self.graphs.items():
            filename = f"family_tree_{dynasty}"
            graph.render(filename, format="png", cleanup=True)
            print(f"Family tree for {dynasty} saved as {filename}.png")


if __name__ == "__main__":
    config_loader = ConfigLoader('config')  # Ensure 'config' directory is correct
    tree = FamilyTree("family_history.txt", "title_history.txt", config_loader.config)  # Ensure both files exist
    tree.build_trees()
    tree.render_trees()