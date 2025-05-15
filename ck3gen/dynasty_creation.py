import json
import logging
import os  # Add this import
from ck3gen.config_loader import LOADED_INFO_FILES

def generate_dynasty_definitions(config_file, output_file="dynasty_definitions.txt"):
    """Generates dynasty definitions from an initialization JSON file."""
    
    # Set output folder and ensure it exists
    output_folder = "Character and Title files"
    os.makedirs(output_folder, exist_ok=True)

    # Full path for the output file
    output_path = os.path.join(output_folder, output_file)

    try:
        with open(config_file, "r", encoding="utf-8") as file:
            config = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error reading {config_file}: {e}")
        return
    
    dynasties = config.get("dynasties", [])
    
    with open(output_path, "w", encoding="utf-8") as file:
        for dynasty in dynasties:
            dynasty_id = dynasty.get("dynastyID", "").replace("dynasty_", "")
            culture_id = dynasty.get("cultureID", "unknown_culture")
            
            if not dynasty_id:
                logging.warning("Skipping dynasty with missing dynastyID.")
                continue
            
            file.write(f"dynasty_{dynasty_id} = {{\n")
            file.write(f"\tname = \"dynn_{dynasty_id}\"\n")
            file.write(f"\tculture = \"{culture_id}\"\n")
            file.write(f"\tmotto = dynn_{dynasty_id}_motto\n")
            file.write("}\n\n")
    if LOADED_INFO_FILES:
        logging.info(f"Dynasty definitions exported to {output_path}.")

def generate_dynasty_name_localization(config_file, output_file="lotr_dynasty_names_l_english.yml"):
    """Generates dynasty names from an initialization JSON file."""
    
    # Set output folder and ensure it exists
    output_folder = "Character and Title files"
    os.makedirs(output_folder, exist_ok=True)

    # Full path for the output file
    output_path = os.path.join(output_folder, output_file)

    try:
        with open(config_file, "r", encoding="utf-8") as file:
            config = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error reading {config_file}: {e}")
        return
    
    dynasties = config.get("dynasties", [])
    
    with open(output_path, "w", encoding="utf-8") as file:
        for dynasty in dynasties:
            dynasty_id = dynasty.get("dynastyID", "").replace("dynasty_", "")
            dynasty_name = dynasty.get("dynastyName", "")
            
            if not dynasty_name:
                logging.warning("Skipping dynasty with missing dynastyName.")
                continue
        
            file.write(f"dynn_{dynasty_id}: \"{dynasty_name}\"""\n")
    if LOADED_INFO_FILES:
        logging.info(f"Dynasty names exported to {output_path}.")

def generate_dynasty_motto_localization(config_file, output_file="lotr_mottos_l_english.yml"):
    """Generates dynasty names from an initialization JSON file."""
    
    # Set output folder and ensure it exists
    output_folder = "Character and Title files"
    os.makedirs(output_folder, exist_ok=True)

    # Full path for the output file
    output_path = os.path.join(output_folder, output_file)

    try:
        with open(config_file, "r", encoding="utf-8") as file:
            config = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error reading {config_file}: {e}")
        return
    
    dynasties = config.get("dynasties", [])
    
    with open(output_path, "w", encoding="utf-8") as file:
        for dynasty in dynasties:
            dynasty_id = dynasty.get("dynastyID", "").replace("dynasty_", "")
            dynastyMotto = dynasty.get("dynastyMotto", "")
            
            if dynastyMotto is not None and dynastyMotto == "":
                print(f"Dynasty Motto: {dynastyMotto}")
                logging.warning("Skipping dynasty with missing dynastyMotto.")
                continue
        
            file.write(f"dynn_{dynasty_id}_motto: \"{dynastyMotto}\"""\n")
    if LOADED_INFO_FILES:
        logging.info(f"Dynasty Mottos exported to {output_path}.")
