import random
import json
from typing import List, Dict, Generator
from models import CK3Character, CK3Dynasty, LifeStage
from abc import ABC, abstractmethod
from config_manager import ConfigManager

class LifeStageStrategy(ABC):
    @abstractmethod
    def determine_stage(self, age: int) -> LifeStage:
        pass

class HumanLifeStageStrategy(LifeStageStrategy):
    def determine_stage(self, age: int) -> LifeStage:
        if age < 3:
            return LifeStage.INFANT
        elif age < 16:
            return LifeStage.CHILD
        elif age < 50:
            return LifeStage.ADULT
        else:
            return LifeStage.SENIOR

class ElfLifeStageStrategy(LifeStageStrategy):
    def determine_stage(self, age: int) -> LifeStage:
        if age < 10:
            return LifeStage.INFANT
        elif age < 50:
            return LifeStage.CHILD
        elif age < 500:
            return LifeStage.ADULT
        else:
            return LifeStage.SENIOR

class SimulationEngine:
    def __init__(self, config_manager: ConfigManager, strategy: LifeStageStrategy):
        self.config_manager = config_manager
        self.life_stages_config = self.config_manager.get_life_stages()
        self.traits_config = self.config_manager.get_traits().get("traits", {})
        self.strategy = strategy
        self.characters: Dict[str, CK3Character] = {}
        self.dynasties: Dict[str, CK3Dynasty] = {}
        self.current_year = 0
        self.next_char_id = 1

    def add_character(self, character: CK3Character) -> None:
        self.characters[character.id] = character

    def add_dynasty(self, dynasty: CK3Dynasty) -> None:
        self.dynasties[dynasty.id] = dynasty

    def _inherit_traits(self, father: CK3Character, mother: CK3Character) -> List[str]:
        inherited_traits = set()
        parent_traits = set(father.traits + mother.traits)
        
        for trait_name, rules in self.traits_config.items():
            inheritance_chance = rules.get("inheritance_chance", 0.0)
            mutation_chance = rules.get("mutation_chance", 0.0)
            
            if trait_name in parent_traits:
                if random.random() < inheritance_chance:
                    inherited_traits.add(trait_name)
            else:
                if random.random() < mutation_chance:
                    inherited_traits.add(trait_name)
                    
        return list(inherited_traits)

    def tick_year(self) -> Generator[str, None, None]:
        self.current_year += 1
        yield f"Year {self.current_year} begins."
        
        living_characters = [c for c in self.characters.values() if c.is_alive]
        
        for char in living_characters:
            age = self.current_year - char.birth_year
            char.life_stage = self.strategy.determine_stage(age)
            
            # Death Check
            mortality_rate = self.life_stages_config.get("mortality_rates", {}).get(char.life_stage.value, 0.01)
            if random.random() < mortality_rate:
                char.is_alive = False
                char.death_year = self.current_year
                yield f"Year {self.current_year}: Character {char.name} ({char.id}) died at age {age}."
                continue
            
            # Marriage Check
            if char.life_stage == LifeStage.ADULT and not char.spouse_id:
                marriage_rate = self.life_stages_config.get("marriage_rates", {}).get(char.life_stage.value, 0.05)
                if random.random() < marriage_rate:
                    # Find a spouse
                    eligible_spouses = [
                        c for c in living_characters 
                        if c.id != char.id and c.is_alive and not c.spouse_id and c.life_stage == LifeStage.ADULT
                    ]
                    if eligible_spouses:
                        spouse = random.choice(eligible_spouses)
                        char.spouse_id = spouse.id
                        spouse.spouse_id = char.id
                        yield f"Year {self.current_year}: Character {char.name} ({char.id}) married {spouse.name} ({spouse.id})."

            # Conception Check
            if char.spouse_id and char.life_stage == LifeStage.ADULT:
                # Only one partner rolls for conception to avoid double counting
                if int(char.id) < int(char.spouse_id):
                    fertility_rate = self.life_stages_config.get("fertility_rates", {}).get(char.life_stage.value, 0.1)
                    if random.random() < fertility_rate:
                        child_id = str(self.next_char_id)
                        self.next_char_id += 1
                        
                        spouse = self.characters[char.spouse_id]
                        child_traits = self._inherit_traits(char, spouse)
                        
                        child = CK3Character(
                            id=child_id,
                            name=f"Child_{child_id}",
                            dynasty_id=char.dynasty_id,
                            birth_year=self.current_year,
                            father_id=char.id,
                            mother_id=char.spouse_id,
                            traits=child_traits
                        )
                        self.add_character(child)
                        trait_str = f" with traits: {', '.join(child_traits)}" if child_traits else ""
                        yield f"Year {self.current_year}: Character {char.name} ({char.id}) and {spouse.name} had a child: {child.name} ({child.id}){trait_str}."

    def run_simulation(self, start_year: int, end_year: int) -> Generator[str, None, None]:
        self.current_year = start_year - 1
        for year in range(start_year, end_year + 1):
            for log in self.tick_year():
                yield log
