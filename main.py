import logging
from config_loader import ConfigLoader
from name_loader import NameLoader
from simulation import Simulation
from character import Character
from title_history import TitleHistory
from utils import generate_char_id, generate_random_date
import random

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def main():
    setup_logging()
    try:
        config_loader = ConfigLoader('config')  # Ensure 'config' directory is correct
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
        gender_law = dynasty_config['genderLaw']
        is_house = dynasty_config['isHouse']
        progenitor_birth_year = dynasty_config['progenitorMaleBirthYear']
        dynasty_prefix = dynasty_id.split('_')[1] if '_' in dynasty_id else dynasty_id

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
            is_progenitor=True
        )
        simulation.add_character_to_pool(progenitor_male)
        simulation.all_characters.append(progenitor_male)
        if len(simulation.all_characters) == 1:  # First character gets the title
            simulation.title_history.assign_initial_holder(progenitor_male)

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
            is_progenitor=True
        )
        simulation.add_character_to_pool(progenitor_female)
        simulation.all_characters.append(progenitor_female)

        # Marry them
        marriage_year = progenitor_male.birth_year + life_stages_config.get('marriageMinAge', 18)
        simulation.marry_characters(progenitor_male, progenitor_female, marriage_year)

    # Run the simulation
    simulation.run_simulation()

    # Export characters
    simulation.export_characters("family_history.txt")

    #Export Title History
    simulation.title_history.export_title_history("title_history.txt")

if __name__ == "__main__":
    main()
