import re
import graphviz

class FamilyTree:
    def __init__(self, filename):
        self.characters = {}
        self.load_characters(filename)
        self.graph = graphviz.Digraph(comment="Family Tree")

    def load_characters(self, filename):
        """Parse the .txt file to extract character details."""
        with open(filename, "r", encoding="utf-8") as f:  # Ensure UTF-8 encoding
            data = f.read()

        # Regex to find each character block
        character_blocks = re.findall(r"(\w+) = \{\s*((?:[^{}]*|\{(?:[^{}]*|\{[^}]*\})*\})*)\s*\}", data, re.DOTALL)


        for identifier, content in character_blocks:
            char_data = {"id": identifier}

            # Extracting values correctly
            char_data["id"] = identifier
            char_data["name"] = self.extract_value(r"name\s*=\s*(\w+)", content)
            char_data["father"] = self.extract_value(r"father\s*=\s*(\w+)", content, default=None)
            char_data["mother"] = self.extract_value(r"mother\s*=\s*(\w+)", content, default=None)
            
            # Birth and Death extraction (Updated)# For birth year extraction
            birth_match = re.search(r"(\d{4})\.\d{2}\.\d{2}\s*=\s*\{\s*birth\s*=\s*yes", content)

            # For death year extraction (with nested death details)
            death_match = re.search(r"(\d{4})\.\d{2}\.\d{2}\s*=\s*\{\s*death", content, re.DOTALL)

            # print("Birth Year: " + birth_match.group(1))

            if death_match:
                # print("Death Year: " + death_match.group(1))
                char_data["death_year"] = death_match.group(1)
            else:
                print("No death date found.")
                char_data["death_year"] = "Unknown"

            char_data["birth_year"] = birth_match.group(1) if birth_match else "Unknown"
            char_data["death_year"] = death_match.group(1) if death_match else "Unknown"


            self.characters[identifier] = char_data

    def extract_value(self, pattern, text, default="Unknown"):
        """Helper function to extract values from a text block."""
        match = re.search(pattern, text)
        return match.group(1) if match else default

    def build_tree(self):
        """Generate a family tree visualization."""
        for char in self.characters.values():
            label = f"{char['id']}\\nBY: {char['birth_year']}\\nDY: {char['death_year']}"
            self.graph.node(char["id"], label=label)

            # Draw edges for parents
            if char["father"] and char["father"] in self.characters:
                self.graph.edge(char["father"], char["id"])
            if char["mother"] and char["mother"] in self.characters:
                self.graph.edge(char["mother"], char["id"])

    def render_tree(self, filename="family_tree"):
        """Render the family tree to a file."""
        self.graph.render(filename, format="png", cleanup=True)
        print(f"Family tree saved as {filename}.png")

if __name__ == "__main__":
    tree = FamilyTree("family_history.txt")  # Make sure this matches your file name
    tree.build_tree()
    tree.render_tree()
