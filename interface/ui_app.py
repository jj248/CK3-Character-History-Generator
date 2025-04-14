import logging
import streamlit as st
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
@st.cache_data(show_spinner=False)
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

def main():
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
    sorted_dynasties = sorted(config.get('dynasties', []), key=lambda d: d['dynastyID'].lower())
    
    for dynasty in sorted_dynasties:
        current_value = dynasty.get('gender_law', gender_options[0])
        with st.expander(f"Dynasty: {dynasty['dynastyID']}", expanded=False):
            dynasty['dynastyName'] = st.text_input("Dynasty Name", dynasty["dynastyName"], key=f"name_{i}")
            dynasty['dynastyMotto'] = st.text_input("Dynasty Motto", dynasty["dynastyMotto"], key=f"motto_{i}")
            dynasty['dynastyID'] = st.text_input("Dynasty ID", dynasty["dynastyID"], key=f"id_{i}")
            dynasty['cultureID'] = st.text_input("Culture ID", dynasty["cultureID"], key=f"culture_{i}")
            dynasty['faithID'] = st.text_input("Religion ID", dynasty["faithID"], key=f"faith_{i}")
            dynasty['faithID'] = st.text_input("Progenitor Birth Year", dynasty["progenitorMaleBirthYear"], key=f"birth_year_{i}")
            dynasty["gender_law"] = st.selectbox("Gender Law", gender_options, index=gender_options.index(current_value), key=f"gender_{i}")
            dynasty['isHouse'] = st.checkbox("Is House?", dynasty["isHouse"], key=f"house_{i}")
            i += 1
            updated = True  # Flag for saving after form

    # Save updated values
    if updated and st.button("💾 Save Changes"):
        save_config(config)
        st.success("Configuration saved.")

if __name__ == "__main__":
    main()