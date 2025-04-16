import base64
import logging
from pathlib import Path
import streamlit as st
import sys
import os
import matplotlib.pyplot as plt

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
def load_config(config_path):
    with open(config_path, "r") as f:
        return json.load(f)

# Save config
def save_config(config_data, config_path):
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=4)

# Reset config to default
def reset_to_default():
    with open(DEFAULT_CONFIG_PATH) as f:
        default_data = json.load(f)
    save_config(default_data, "config/initialization.json")
    st.session_state["reset_triggered"] = True

def display_dynasty_config():
    st.title("CK3 Character History Generator")
    if "config_loaded" not in st.session_state:
        st.session_state["config_loaded"] = False

    # Load config only if not already loaded
    if not st.session_state["config_loaded"]:
        config = load_config("config/initialization.json")
        st.session_state["config_loaded"] = True  # Mark the config as loaded
    else:
        config = load_config("config/initialization.json")

    # Disabling condition: Until the config is loaded, set the 'disabled' flag
    disabled = not st.session_state["config_loaded"]

    if st.button("🔄 Reset Dynasties", disabled=disabled):
        reset_to_default()
        
    # If reset was triggered, reload config and clear flag
    if st.session_state.get("reset_triggered", False):
        config = load_config("config/initialization.json")
        st.success("Configuration reset to default.")
        st.session_state["reset_triggered"] = False
    else:
        config = load_config("config/initialization.json")

    # Split the layout into 3 horizontal columns
    col1, col2 = st.columns(2)

    # Text inputs inside columns
    with col1:
        min_year = st.text_input("Start Year", value=str(config.get("minYear", "0")), key="min_year_input")
    with col2:
        max_year = st.text_input("End Year", value=str(config.get("maxYear", "1000")), key="max_year_input")
    max_generations = st.slider("Maximum Number of Generations", min_value=1, max_value=200, value=config.get('generationMax'), step=1, key="max_gen_characters")

    # Save button
    if st.button("💾 Save Global Settings", disabled=disabled):
        try:
            config["minYear"] = int(min_year)
            config["maxYear"] = int(max_year)
            config["generationMax"] = int(max_generations)
            save_config(config, "config/initialization.json")
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
            new_id = st.text_input("Dynasty ID", disabled=disabled)
            new_name = st.text_input("Dynasty Name", disabled=disabled)
            new_motto = st.text_input("Motto", disabled=disabled)
            new_culture = st.text_input("Culture ID", disabled=disabled)
            new_faith = st.text_input("Faith ID", disabled=disabled)
            new_gender_law = st.selectbox("Gender Law", ["AGNATIC", "AGNATIC_COGNATIC", "ABSOLUTE_COGNATIC", "ENATIC", "ENATIC_COGNATIC"], disabled=disabled)
            new_succession = st.selectbox("Succession", ["PRIMOGENITURE", "ULTIMOGENITURE", "SENIORITY"], disabled=disabled)
            new_house = st.checkbox("Is House?", value=False, disabled=disabled)
            new_year = st.number_input("Progenitor Birth Year", value=6000, step=1, disabled=disabled)
            submit = st.form_submit_button("Add Dynasty", disabled=disabled)

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
            save_config(config, "config/initialization.json")  # Your save function
            st.rerun()

    config['dynasties'].sort(key=lambda d: d['dynastyID'].lower())
    for i, dynasty in enumerate(config['dynasties']):
        current_value = dynasty.get('gender_law', gender_options[0])
        
        # Create two columns for header: Dynasty title and Delete button
        col1, col2 = st.columns([11, 1])  # Adjust widths as needed

        with col1:
            st.markdown(f"#### Dynasty: {dynasty['dynastyID']}")
        with col2:
            if st.button("❌", key=f"delete_dynasty_{i}", disabled=disabled):
                config['dynasties'].remove(dynasty)
                save_config(config, "config/initialization.json")
                st.rerun()

        with st.expander("Edit Dynasty Details", expanded=False):
            dynasty['dynastyName'] = st.text_input("Dynasty Name", dynasty["dynastyName"], key=f"name_{i}", disabled=disabled)
            dynasty['dynastyMotto'] = st.text_input("Dynasty Motto", dynasty["dynastyMotto"], key=f"motto_{i}", disabled=disabled)
            dynasty['dynastyID'] = st.text_input("Dynasty ID", dynasty["dynastyID"], key=f"id_{i}", disabled=disabled)
            dynasty['cultureID'] = st.text_input("Culture ID", dynasty["cultureID"], key=f"culture_{i}", disabled=disabled)
            dynasty['faithID'] = st.text_input("Religion ID", dynasty["faithID"], key=f"faith_{i}", disabled=disabled)
            dynasty['progenitorMaleBirthYear'] = st.number_input("Progenitor Birth Year", value=dynasty["progenitorMaleBirthYear"], step=1, key=f"birth_year_{i}", disabled=disabled)
            dynasty["gender_law"] = st.selectbox("Gender Law", gender_options, index=gender_options.index(current_value), key=f"gender_{i}", disabled=disabled)
            dynasty['isHouse'] = st.checkbox("Is House?", dynasty["isHouse"], key=f"house_{i}", disabled=disabled)
            
            updated = True

    # Save updated values
    if updated and st.button("💾 Save Dynasty Changes", disabled=disabled):
        save_config(config, "config/initialization.json")
        st.success("Configuration saved.")
        
    if st.button("Run Simulation", disabled=disabled):
        run_main()

def display_event_config():
    st.title("CK3 Character History Generator")
    st.subheader("📜 Negative Events Impacting Death Rates")
    if "config_loaded" not in st.session_state:
        st.session_state["config_loaded"] = False

    # Load config only if not already loaded
    if not st.session_state["config_loaded"]:
        config = load_config("config/initialization.json")
        st.session_state["config_loaded"] = True  # Mark the config as loaded
    else:
        config = load_config("config/initialization.json")

    # Disabling condition: Until the config is loaded, set the 'disabled' flag
    disabled = not st.session_state["config_loaded"]

    if st.button("🔄 Reset Events", disabled=disabled):
        reset_to_default()
        
    # If reset was triggered, reload config and clear flag
    if st.session_state.get("reset_triggered", False):
        config = load_config("config/initialization.json")
        st.success("Events reset to default.")
        st.session_state["reset_triggered"] = False
    else:
        config = load_config("config/initialization.json")

    with st.expander("➕ Add New Event"):
        with st.form(key="add_event"):
            new_eventID = st.text_input("eventID", disabled=disabled)
            new_startYear = st.number_input("startYear", value=6000, step=1, disabled=disabled)
            new_endYear = st.number_input("endYear", value=6500, step=1, disabled=disabled)
            new_deathReason = st.text_input("deathReason", disabled=disabled)
            new_deathMultiplier = st.number_input("deathMultiplier", min_value=0.0, max_value=1.0, value=0.5, step=0.1, disabled=disabled)
            new_characterAgeStart = st.number_input("startYear", min_value=0, max_value=120, value=0, step=1, disabled=disabled)
            new_characterAgeEnd = st.number_input("startYear", min_value=0, max_value=120, value=60, step=1, disabled=disabled)
            submit = st.form_submit_button("Add Event", disabled=disabled)

        if submit:
            new_event = {
                "eventID": new_eventID,
                "startYear": new_startYear,
                "endYear": new_endYear,
                "deathReason": new_deathReason,
                "deathMultiplier": new_deathMultiplier,
                "characterAgeStart": new_characterAgeStart,
                "characterAgeEnd": new_characterAgeEnd,
            }
            config['events'].append(new_event)
            save_config(config, "config/initialization.json")  # Your save function
            st.rerun()
            
    config['events'].sort(key=lambda d: d['eventID'].lower())
    for i, event in enumerate(config['events']):
        # Create two columns for header: Dynasty title and Delete button
        col1, col2 = st.columns([11, 1])  # Adjust widths as needed

        with col1:
            st.markdown(f"#### Event: {event['eventID']}")
        with col2:
            if st.button("❌", key=f"delete_event_{i}", disabled=disabled):
                config['events'].remove(event)
                save_config(config, "config/initialization.json")
                st.rerun()

        with st.expander("Edit Event Details", expanded=False):
            event['eventID'] = st.text_input("event ID", event["eventID"], key=f"eventID_{i}", disabled=disabled)
            event['startYear'] = st.number_input("Start Year", value=event["startYear"], step=1, key=f"startYear_{i}", disabled=disabled)
            event['endYear'] = st.number_input("End Year", value=event["endYear"], step=1, key=f"endYear_{i}", disabled=disabled)
            event['deathReason'] = st.text_input("Death Reason", event["deathReason"], key=f"deathReason_{i}", disabled=disabled)
            event['deathMultiplier'] = st.number_input("Lethality Factor", min_value=0.0, max_value=1.0, value=event["deathMultiplier"], step=0.1, key=f"deathMultiplier_{i}", disabled=disabled)
            event['characterAgeStart'] = st.number_input("Character Minimum Age", min_value=0, max_value=120, value=event["characterAgeStart"], step=1, key=f"characterAgeStart_{i}", disabled=disabled)
            event["characterAgeEnd"] = st.number_input("Character Maximum Age", min_value=0, max_value=120, value=event["characterAgeEnd"], step=1, key=f"characterAgeEnd_{i}", disabled=disabled)
             
            updated = True

    # Save updated values
    if updated and st.button("💾 Save Event Changes", disabled=disabled):
        save_config(config, "config/initialization.json")
        st.success("Configuration saved.")

def display_life_stage_config():
    st.title("CK3 Character History Generator")
    st.subheader("💉 Life Cycle Modifiers")
    if "config_loaded" not in st.session_state:
        st.session_state["config_loaded"] = False

    # Load config only if not already loaded
    if not st.session_state["config_loaded"]:
        config = load_config("config/life_stages.json")
        st.session_state["config_loaded"] = True  # Mark the config as loaded
    else:
        config = load_config("config/life_stages.json")

    # Disabling condition: Until the config is loaded, set the 'disabled' flag
    disabled = not st.session_state["config_loaded"]

    if st.button("🔄 Reset Life Cycle Modifiers", disabled=disabled):
        reset_to_default()
        
    # If reset was triggered, reload config and clear flag
    if st.session_state.get("reset_triggered", False):
        config = load_config("config/life_stages.json")
        st.success("Life Cycle Modifiers reset to default.")
        st.session_state["reset_triggered"] = False
    else:
        config = load_config("config/life_stages.json")

    config['marriageMaxAgeDifference'] = st.number_input("Maximum Difference in Age Between Spouses", min_value=0, max_value=30, value=config["marriageMaxAgeDifference"], key=f"marriageMaxAgeDifference", disabled=disabled)
    config['maximumNumberOfChildren'] = st.number_input("Maximum Number of Children", value=config["maximumNumberOfChildren"], min_value=1, max_value=10, step=1, key=f"maximumNumberOfChildren", disabled=disabled)
    config['minimumYearsBetweenChildren'] = st.number_input("Minimum Years Between Children", min_value=1, max_value=10, value=config["minimumYearsBetweenChildren"], step=1, key=f"minimumYearsBetweenChildren", disabled=disabled)
    config['bastardyChanceMale'] = st.number_input("Chance for Male Bastards", min_value=0.0000, max_value=1.0000, value=config["bastardyChanceMale"], step=0.0005, key=f"bastardyChanceMale", disabled=disabled)
    config['bastardyChanceFemale'] = st.number_input("Chance for Female Bastards", min_value=0.0000, max_value=1.0000, value=config["bastardyChanceFemale"], step=0.0005, key=f"bastardyChanceFemale", disabled=disabled)
        
    # Save updated values
    if st.button("💾 Save Life Cycle Modifier Changes", disabled=disabled):
        save_config(config, "config/life_stages.json")
        st.success("Configuration saved.")
    
    display_desperation_marriage_rates(config)
    display_mortality_rates(config)
    display_marriage_rates(config)
    display_fertility_rates(config)
    
    
def display_desperation_marriage_rates(config):
    st.subheader("Desperation Marriage Rates")
    desperationMarriageRates = config['desperationMarriageRates']
    
    # Age range for the data
    ages = list(range(len(desperationMarriageRates)))

    # Plot desperation marriage rates
    plt.figure(figsize=(12, 6))
    plt.plot(ages, desperationMarriageRates, label='Desperation Marriage Rate', color='red')
    plt.ylim(0.0, 1.0)
    plt.xlabel('Age')
    plt.ylabel('Rate')
    plt.title('Desperation Marriage Rates by Age')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    st.pyplot(plt.gcf())
    plt.clf()
    
def display_mortality_rates(config):
    st.subheader("Mortality Rates for Male/Female")

    # Slider for adjusting mortality rates
    maleMultiplier = st.slider(
        "Adjust Male Mortality Rate Multiplier",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.01
    )

    # Load mortality rate data
    maleMortalityRates = config['mortalityRates']['Male']
    femaleMortalityRates = config['mortalityRates']['Female']
    maleMR = list(range(len(maleMortalityRates)))
    femaleMR = list(range(len(femaleMortalityRates)))

    # Apply multiplier
    adjustedMaleRates = [rate * maleMultiplier for rate in maleMortalityRates]

    # Plotting
    plt.figure(figsize=(12, 6))
    plt.plot(maleMR, adjustedMaleRates, label='Male Mortality Rates', color='red')
    plt.ylim(0.0, 1.0)
    plt.xlabel('Age')
    plt.ylabel('Rate')
    plt.title('Male Mortality Rate by Age (Adjusted)')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    st.pyplot(plt.gcf())
    plt.clf()
    
    # Slider for adjusting female mortality rates
    femaleMultiplier = st.slider(
        "Adjust Female Mortality Rate Multiplier",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.01
    )
    
    # Apply multiplier
    adjustedFemaleRates = [rate * femaleMultiplier for rate in femaleMortalityRates]
    
    # Plot desperation marriage rates
    plt.figure(figsize=(12, 6))
    plt.plot(femaleMR, adjustedFemaleRates, label='Female Mortality Rate', color='red')
    plt.ylim(0.0, 1.0)
    plt.xlabel('Age')
    plt.ylabel('Rate')
    plt.title('Female Mortality Rate by Age')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    st.pyplot(plt.gcf())
    plt.clf()

def display_marriage_rates(config):
    st.subheader("Marriage Rates for Male/Female")
    
    # Slider for adjusting mortality rates
    maleMultiplier = st.slider(
        "Adjust Male Marriage Rate Multiplier",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.01
    )
    
    maleMarriageRates = config['marriageRates']['Male']
    femaleMarriageRates = config['marriageRates']['Female']
    
    # Age range for the data
    maleMR = list(range(len(maleMarriageRates)))
    femaleMR = list(range(len(femaleMarriageRates)))

    # Apply multiplier
    adjustedMaleRates = [rate * maleMultiplier for rate in maleMarriageRates]

    # Plot desperation marriage rates
    plt.figure(figsize=(12, 6))
    plt.plot(maleMR, adjustedMaleRates, label='Male marriage Rates', color='red')
    plt.ylim(0.0, 1.0)
    plt.xlabel('Age')
    plt.ylabel('Rate')
    plt.title('Male Marriage Rate by Age')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    st.pyplot(plt.gcf())
    plt.clf()
    
    # Slider for adjusting mortality rates
    femaleMultiplier = st.slider(
        "Adjust Female Marriage Rate Multiplier",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.01
    )
    # Apply multiplier
    adjustedFemaleRates = [rate * femaleMultiplier for rate in femaleMarriageRates]

    # Plot desperation marriage rates
    plt.figure(figsize=(12, 6))
    plt.plot(femaleMR, adjustedFemaleRates, label='Female marriage Rate', color='red')
    plt.ylim(0.0, 1.0)
    plt.xlabel('Age')
    plt.ylabel('Rate')
    plt.title('Female Marriage Rate by Age')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    st.pyplot(plt.gcf())
    plt.clf()

def display_fertility_rates(config):
    st.subheader("Fertility Rates for Male/Female")

    maleFertilityRates = config['fertilityRates']['Male']
    femaleFertilityRates = config['fertilityRates']['Female']
    
    # Age range for the data
    maleMR = list(range(len(maleFertilityRates)))
    femaleMR = list(range(len(femaleFertilityRates)))

    
    # Slider for adjusting female mortality rates
    maleMultiplier = st.slider(
        "Adjust Male Fertility Rate Multiplier",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.01
    )
    
    # Apply multiplier
    adjustedMaleRates = [rate * maleMultiplier for rate in maleFertilityRates]

    # Plot desperation fertility rates
    plt.figure(figsize=(12, 6))
    plt.plot(maleMR, adjustedMaleRates, label='Male fertility Rates', color='red')
    plt.ylim(0.0, 1.0)
    plt.xlabel('Age')
    plt.ylabel('Rate')
    plt.title('Male fertility Rate by Age')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    st.pyplot(plt.gcf())
    plt.clf()
    
    # Slider for adjusting female mortality rates
    femaleMultiplier = st.slider(
        "Adjust Female Fertility Rate Multiplier",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.01
    )
    
    # Apply multiplier
    adjustedFemaleRates = [rate * femaleMultiplier for rate in femaleFertilityRates]

    # Plot desperation fertility rates
    plt.figure(figsize=(12, 6))
    plt.plot(femaleMR, adjustedFemaleRates, label='Female fertility Rate', color='red')
    plt.ylim(0.0, 1.0)
    plt.xlabel('Age')
    plt.ylabel('Rate')
    plt.title('Female fertility Rate by Age')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    st.pyplot(plt.gcf())
    plt.clf()

def display_generated_images(image_folder: str):
    st.title("CK3 Character History Generator")
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
    tab1, tab2, tab3, tab4 = st.tabs(["🏛️ Dynasty Settings", "🌳 Dynasty Trees", "📜 Negative Events", "💉 Life Cycle Modifiers"])

    with tab1:
        display_dynasty_config()

    with tab2:
        display_generated_images("Dynasty Preview/")

    with tab3:
        display_event_config()
    
    with tab4:
        display_life_stage_config()

if __name__ == "__main__":
    main()