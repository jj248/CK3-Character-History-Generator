from backend.core.base_generator import BaseGenerator
from backend.models.character import CK3Character

class CharacterHistoryGenerator(BaseGenerator[CK3Character]):
    """
    Concrete generator for CK3 Character History.
    """

    def generate_script(self, entity: CK3Character) -> str:
        """
        Generates the CK3 script string for a character.

        Args:
            entity (CK3Character): The character model.

        Returns:
            str: The formatted CK3 script string.
        """
        lines = []
        lines.append(f"{entity.id} = {{")
        lines.append(f"\tname = \"{entity.name}\"")
        
        if entity.is_female:
            lines.append("\tfemale = yes")
            
        if entity.dynasty_id:
            lines.append(f"\tdynasty = {entity.dynasty_id}")
            
        lines.append(f"\tculture = {entity.culture}")
        lines.append(f"\treligion = {entity.religion}")
        
        for trait in entity.traits:
            lines.append(f"\ttrait = {trait}")
            
        stats = entity.stats
        if any([stats.diplomacy, stats.martial, stats.stewardship, stats.intrigue, stats.learning, stats.prowess]):
            lines.append(f"\tdiplomacy = {stats.diplomacy}")
            lines.append(f"\tmartial = {stats.martial}")
            lines.append(f"\tstewardship = {stats.stewardship}")
            lines.append(f"\tintrigue = {stats.intrigue}")
            lines.append(f"\tlearning = {stats.learning}")
            lines.append(f"\tprowess = {stats.prowess}")
            
        lines.append(f"\t{entity.birth_date} = {{")
        lines.append("\t\tbirth = yes")
        lines.append("\t}")
        
        if entity.death_date:
            lines.append(f"\t{entity.death_date} = {{")
            lines.append("\t\tdeath = yes")
            lines.append("\t}")
            
        lines.append("}")
        return "\n".join(lines)

    def validate(self, entity: CK3Character) -> bool:
        """
        Validates the character model.

        Args:
            entity (CK3Character): The character model.

        Returns:
            bool: True if valid.
        """
        if not entity.id or not entity.name:
            return False
        if not entity.culture or not entity.religion:
            return False
        if not entity.birth_date:
            return False
        return True
