import json
import logging
import os  # Add this import

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
    
    logging.info(f"Dynasty definitions exported to {output_path}.")
