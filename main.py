import logging
import os
import sys
from ck3gen.config_loader import ConfigLoader
from ck3gen.family_tree import FamilyTree
from ck3gen.name_loader import NameLoader
from ck3gen.simulation import Simulation
from ck3gen.character import Character
from ck3gen.title_history import CharacterLoader
from ck3gen.title_history import TitleHistory
from ck3gen.dynasty_creation import generate_dynasty_definitions, generate_dynasty_name_localization, generate_dynasty_motto_localization
from utils.utils import generate_char_id, generate_random_date
import random


def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def run_main():
    setup_logging()
    try:
        config_loader = ConfigLoader('config')  # Ensure 'config' directory is correct
        Character.DYNASTY_LANGUAGE_RULES = config_loader.get_language_rules()
        
        dynasty_config_path = get_resource_path("config/initialization.json")
        generate_dynasty_definitions(dynasty_config_path, "dynasty_definitions.txt")
        generate_dynasty_name_localization(dynasty_config_path, "lotr_dynasty_names_l_english.yml")
        generate_dynasty_motto_localization(dynasty_config_path, "lotr_mottos_l_english.yml")
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        return

    name_loader = NameLoader('name_lists')
    simulation = Simulation(config_loader.config, name_loader)

    # Generate progenitor characters for each dynasty
    initialization_config = config_loader.get_initialization_config()
    skills_and_traits_config = config_loader.get_skills_and_traits_config()
    life_stages_config = config_loader.get_life_stages_config()

    for dynasty_config in initialization_config.get('dynasties', []):
        dynasty_id = dynasty_config['dynastyID']
        culture_id = dynasty_config['cultureID']
        religion_id = dynasty_config['faithID']
        gender_law = dynasty_config['gender_law']
        is_house = dynasty_config['isHouse']
        progenitor_birth_year = dynasty_config['progenitorMaleBirthYear']
        tier = dynasty_config.get('numenorBloodTier', 0)
        dynasty_prefix = dynasty_id.split('_')[1] if '_' in dynasty_id else dynasty_id

        if gender_law == "ENATIC" or gender_law == "ENATIC_COGNATIC":
            # Create progenitor female
            progenitor_male_char_id = generate_char_id(dynasty_prefix, simulation.dynasty_char_counters)
            progenitor_male_name = name_loader.load_names(culture_id, "female")
            progenitor_male = Character(
                char_id=progenitor_male_char_id,
                name=progenitor_male_name,
                sex="Female",
                birth_year=progenitor_birth_year,
                dynasty=dynasty_id,
                is_house=is_house,
                culture=culture_id,
                religion=religion_id,
                gender_law=gender_law,
                sexuality_distribution=skills_and_traits_config['sexualityDistribution'],
                generation=1,
                is_progenitor=True,
                birth_order=1
            )
            progenitor_male.age = 18
            progenitor_male.numenorean_blood_tier = tier
            simulation.add_character_to_pool(progenitor_male)
            simulation.all_characters.append(progenitor_male)

            # Generate progenitor male spouse
            spouse_birth_year = progenitor_birth_year  # Same year as female
            progenitor_female_char_id = generate_char_id(dynasty_prefix, simulation.dynasty_char_counters)
            progenitor_female_name = name_loader.load_names(culture_id, "male")
            progenitor_female = Character(
                char_id=progenitor_female_char_id,
                name=progenitor_female_name,
                sex="Male",
                birth_year=spouse_birth_year,  # Same year
                dynasty=None,  # Lowborn, no dynasty
                is_house=is_house,
                culture=culture_id,
                religion=religion_id,
                gender_law=gender_law,
                sexuality_distribution=skills_and_traits_config['sexualityDistribution'],
                generation=1,
                is_progenitor=True,
                birth_order=1
            )
            progenitor_female.numenorean_blood_tier = tier
            simulation.add_character_to_pool(progenitor_female)
            simulation.all_characters.append(progenitor_female)

            # Marry them
            marriage_year = progenitor_male.birth_year + life_stages_config.get('marriageMinAge', 18)
            simulation.marry_characters(progenitor_male, progenitor_female, marriage_year)
            # Ensure at least 3 children per dynasty
            for i in range(3):
                child_birth_year = marriage_year + i + 1  # Stagger births
                child = simulation.create_child(progenitor_male, progenitor_female, child_birth_year)
                if child:
                    simulation.add_character_to_pool(child)
                    simulation.all_characters.append(child)
        
        else:
            # Create progenitor male
            progenitor_male_char_id = generate_char_id(dynasty_prefix, simulation.dynasty_char_counters)
            progenitor_male_name = name_loader.load_names(culture_id, "male")
            progenitor_male = Character(
                char_id=progenitor_male_char_id,
                name=progenitor_male_name,
                sex="Male",
                birth_year=progenitor_birth_year,
                dynasty=dynasty_id,
                is_house=is_house,
                culture=culture_id,
                religion=religion_id,
                gender_law=gender_law,
                sexuality_distribution=skills_and_traits_config['sexualityDistribution'],
                generation=1,
                is_progenitor=True,
                birth_order=1
            )
            progenitor_male.age = 18
            progenitor_male.numenorean_blood_tier = tier
            simulation.add_character_to_pool(progenitor_male)
            simulation.all_characters.append(progenitor_male)

            # Generate progenitor female spouse
            spouse_birth_year = progenitor_birth_year  # Same year as male
            progenitor_female_char_id = generate_char_id(dynasty_prefix, simulation.dynasty_char_counters)
            progenitor_female_name = name_loader.load_names(culture_id, "female")
            progenitor_female = Character(
                char_id=progenitor_female_char_id,
                name=progenitor_female_name,
                sex="Female",
                birth_year=spouse_birth_year,  # Same year
                dynasty=None,  # Lowborn, no dynasty
                is_house=is_house,
                culture=culture_id,
                religion=religion_id,
                gender_law=gender_law,
                sexuality_distribution=skills_and_traits_config['sexualityDistribution'],
                generation=1,
                is_progenitor=True,
                birth_order=1
            )
            progenitor_female.numenorean_blood_tier = tier
            simulation.add_character_to_pool(progenitor_female)
            simulation.all_characters.append(progenitor_female)

            # Marry them
            marriage_year = progenitor_male.birth_year + life_stages_config.get('marriageMinAge', 18)
            simulation.marry_characters(progenitor_male, progenitor_female, marriage_year)
            # Ensure at least 3 children per dynasty
            for i in range(3):
                child_birth_year = marriage_year + i + 1  # Stagger births
                child = simulation.create_child(progenitor_female, progenitor_male, child_birth_year)
                if child:
                    simulation.add_character_to_pool(child)
                    simulation.all_characters.append(child)

    # Run the simulation
    simulation.run_simulation()

    # Export characters
    simulation.export_characters("family_history.txt")

    # Load character data from family history
    character_loader = CharacterLoader()
    character_loader.load_characters("Character and Title files/family_history.txt")  # Loads characters into memory
    # character_loader.print_family_info()

    dynasty_config_path = get_resource_path("config/initialization.json")
    # # Load title history, passing the CharacterLoader instance
    titles = TitleHistory(character_loader, dynasty_config_path)
    titles.build_title_histories()
    titles.print_title_histories()
    titles.write_title_histories_to_file()

    tree = FamilyTree("Character and Title files/family_history.txt", "Character and Title files/title_history.txt", config_loader.config)  # Ensure both files exist
    tree.build_trees()
    tree.render_trees()

if __name__ == "__main__":
    run_main()
