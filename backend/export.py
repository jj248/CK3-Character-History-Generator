from models import CK3Character, CK3Dynasty
from typing import Dict

def export_graphviz(characters: Dict[str, CK3Character], dynasties: Dict[str, CK3Dynasty]) -> str:
    lines = []
    lines.append("digraph FamilyTree {")
    lines.append("    node [shape=box, fontname=\"Helvetica\"];")
    lines.append("    edge [fontname=\"Helvetica\"];")
    
    for char_id, char in characters.items():
        label = f"{char.name}\\n({char.birth_year} - {char.death_year if char.death_year else 'Present'})"
        lines.append(f"    \"{char_id}\" [label=\"{label}\"];")
        
        if char.father_id:
            lines.append(f"    \"{char.father_id}\" -> \"{char_id}\" [label=\"Father\"];")
        if char.mother_id:
            lines.append(f"    \"{char.mother_id}\" -> \"{char_id}\" [label=\"Mother\"];")
            
    lines.append("}")
    
    # Ensure UTF-8 with BOM
    bom = "\ufeff"
    content = bom + "\n".join(lines)
    return content
