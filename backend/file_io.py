import os
from typing import Dict
from models import CK3Character, CK3Dynasty

class FileIOService:
    def __init__(self, output_dir: str = "Dynasty Preview"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def write_characters(self, characters: Dict[str, CK3Character]) -> None:
        filepath = os.path.join(self.output_dir, "characters.txt")
        # utf-8-sig ensures the file is written with a UTF-8 BOM, required by Paradox
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            for char_id, char in characters.items():
                f.write(f"{char_id} = {{\n")
                f.write(f"\tname = \"{char.name}\"\n")
                f.write(f"\tdynasty = {char.dynasty_id}\n")
                if char.father_id:
                    f.write(f"\tfather = {char.father_id}\n")
                if char.mother_id:
                    f.write(f"\tmother = {char.mother_id}\n")
                for trait in char.traits:
                    f.write(f"\ttrait = {trait}\n")
                f.write(f"\t{char.birth_year}.1.1 = {{\n\t\tbirth = yes\n\t}}\n")
                if not char.is_alive and char.death_year:
                    f.write(f"\t{char.death_year}.1.1 = {{\n\t\tdeath = yes\n\t}}\n")
                f.write("}\n\n")

    def write_dynasties(self, dynasties: Dict[str, CK3Dynasty]) -> None:
        filepath = os.path.join(self.output_dir, "dynasties.txt")
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            for dyn_id, dyn in dynasties.items():
                f.write(f"{dyn_id} = {{\n")
                f.write(f"\tname = \"{dyn.name}\"\n")
                f.write("}\n\n")
