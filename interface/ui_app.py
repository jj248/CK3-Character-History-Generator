import base64
import logging
from pathlib import Path
import streamlit as st
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import run_main
import json
from enum import Enum

CONFIG_PATH="config/initialization.json"
DEFAULT_CONFIG_PATH="config/fallback_config_files/initialization.json"

############################
# Enums for Succession/Gender
############################

class SuccessionType(Enum):
    PRIMOGENITURE = "PRIMOGENITURE"
    ULTIMOGENITURE = "ULTIMOGENITURE"
    SENIORITY = "SENIORITY"

class GenderLaw(Enum):
    AGNATIC = "AGNATIC"
    AGNATIC_COGNATIC = "AGNATIC_COGNATIC"
    ABSOLUTE_COGNATIC = "ABSOLUTE_COGNATIC"
    ENATIC = "ENATIC"
    ENATIC_COGNATIC = "ENATIC_COGNATIC"

# Load config
def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

# Save config
def save_config(config_data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config_data, f, indent=4)

# Reset config to default
def reset_to_default():
    with open(DEFAULT_CONFIG_PATH) as f:
        default_data = json.load(f)
    save_config(default_data)
    st.session_state["reset_triggered"] = True

def display_dynasty_config():
    st.title("CK3 Character History Generator")
    if st.button("🔄 Reset to Default"):
        reset_to_default()
        
    # If reset was triggered, reload config and clear flag
    if st.session_state.get("reset_triggered", False):
        config = load_config()
        st.success("Configuration reset to default.")
        st.session_state["reset_triggered"] = False
    else:
        config = load_config()
    
    # Split the layout into 3 horizontal columns
    col1, col2 = st.columns(2)

    # Text inputs inside columns
    with col1:
        min_year = st.text_input("Start Year", value=str(config.get("minYear", "0")), key="min_year_input")
    with col2:
        max_year = st.text_input("End Year", value=str(config.get("maxYear", "1000")), key="max_year_input")
    max_generations = st.slider("Maximum Number of Generations", min_value=1, max_value=200, value=config.get('generationMax'), step=1, key="max_gen_characters")

    # Save button
    if st.button("💾 Save Global Settings"):
        try:
            config["minYear"] = int(min_year)
            config["maxYear"] = int(max_year)
            config["generationMax"] = int(max_generations)
            save_config(config)
            st.success("Global settings saved successfully!")
        except ValueError:
            st.error("All inputs must be valid integers.")
    
    # Extract enum values as a list
    gender_options = [law.value for law in GenderLaw]
    
    # Dynamically render dynasty accordions
    updated = False
    i = 0
    
    with st.expander("➕ Add New Dynasty"):
        with st.form(key="add_dynasty_form"):
            new_id = st.text_input("Dynasty ID")
            new_name = st.text_input("Dynasty Name")
            new_motto = st.text_input("Motto")
            new_culture = st.text_input("Culture ID")
            new_faith = st.text_input("Faith ID")
            new_gender_law = st.selectbox("Gender Law", ["AGNATIC", "AGNATIC_COGNATIC", "ABSOLUTE_COGNATIC", "ENATIC", "ENATIC_COGNATIC"])
            new_succession = st.selectbox("Succession", ["PRIMOGENITURE", "ULTIMOGENITURE", "SENIORITY"])
            new_house = st.checkbox("Is House?", value=False)
            new_year = st.number_input("Progenitor Birth Year", value=6000, step=1)
            submit = st.form_submit_button("Add Dynasty")

        if submit:
            new_dynasty = {
                "dynastyName": new_name,
                "dynastyMotto": new_motto,
                "succession": new_succession,
                "dynastyID": new_id,
                "isHouse": new_house,
                "faithID": new_faith,
                "cultureID": new_culture,
                "gender_law": new_gender_law,
                "progenitorMaleBirthYear": int(new_year),
                "nameInheritance": {
                    "grandparentNameInheritanceChance": 0.05,
                    "parentNameInheritanceChance": 0.05,
                    "noNameInheritanceChance": 0.9
                }
            }
            config['dynasties'].append(new_dynasty)
            save_config(config)  # Your save function
            st.rerun()

    
    config['dynasties'].sort(key=lambda d: d['dynastyID'].lower())
    for i, dynasty in enumerate(config['dynasties']):
        current_value = dynasty.get('gender_law', gender_options[0])
        with st.expander(f"Dynasty: {dynasty['dynastyID']}", expanded=False):
            dynasty['dynastyName'] = st.text_input("Dynasty Name", dynasty["dynastyName"], key=f"name_{i}")
            dynasty['dynastyMotto'] = st.text_input("Dynasty Motto", dynasty["dynastyMotto"], key=f"motto_{i}")
            dynasty['dynastyID'] = st.text_input("Dynasty ID", dynasty["dynastyID"], key=f"id_{i}")
            dynasty['cultureID'] = st.text_input("Culture ID", dynasty["cultureID"], key=f"culture_{i}")
            dynasty['faithID'] = st.text_input("Religion ID", dynasty["faithID"], key=f"faith_{i}")
            dynasty['progenitorMaleBirthYear'] = st.number_input("Progenitor Birth Year", value=dynasty["progenitorMaleBirthYear"], step=1, key=f"birth_year_{i}")
            dynasty["gender_law"] = st.selectbox("Gender Law", gender_options, index=gender_options.index(current_value), key=f"gender_{i}")
            dynasty['isHouse'] = st.checkbox("Is House?", dynasty["isHouse"], key=f"house_{i}")
            
            if st.button(f"❌ Delete Dynasty {dynasty['dynastyID']}", key=f"delete_{i}"):
                config['dynasties'].remove(dynasty)
                save_config(config)
                st.rerun()
            
            updated = True

    # Save updated values
    if updated and st.button("💾 Save Changes"):
        save_config(config)
        st.success("Configuration saved.")
        
    if st.button("Run Simulation"):
        run_main()
        
def display_generated_images(image_folder: str):
    st.subheader("🧬 Generated Dynastic Trees")

    # Get all image files
    image_paths = sorted(Path(image_folder).glob("family_tree_*.png"))

    if not image_paths:
        st.info("No dynasty tree images found. Run the simulation first.")
        return

    for image_path in image_paths:
        dynasty_id = image_path.stem.replace("family_tree_", "")
        with st.expander(f"Tree for Dynasty: {dynasty_id}", expanded=False):
            image_base64 = base64.b64encode(open(image_path, "rb").read()).decode()
            image_html = f"""
                <div style="overflow-x:auto;">
                    <img src="data:image/png;base64,{image_base64}" style="max-width: 100%; height: auto; transition: transform 0.2s;" 
                         onmouseover="this.style.transform='scale(1.5)'" 
                         onmouseout="this.style.transform='scale(1)'"/>
                </div>
                <p style='text-align:center;'><em>Dynasty Tree: {dynasty_id}</em></p>
            """
            st.markdown(image_html, unsafe_allow_html=True)

            
def main():
    tab1, tab2 = st.tabs(["🏛️ Dynasty Settings", "🌳 Dynasty Trees"])

    with tab1:
        display_dynasty_config()

    with tab2:
        display_generated_images("Dynasty Preview/")

if __name__ == "__main__":
    main()