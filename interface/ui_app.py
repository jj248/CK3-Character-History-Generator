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

############################
# Enums for Succession/Gender
############################
class EventType(Enum):
    event_plague = "event_plague"
    event_war = "event_war"
    event_battle = "event_battle"

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

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.abspath(os.path.join(base_path, '..', relative_path))

# Load config
def load_config(config_path):
    dyn_config_path = get_resource_path(config_path)
    with open(dyn_config_path, "r") as f:
        return json.load(f)

# Save config
def save_config(config_data, config_path):
    dyn_config_path = get_resource_path(config_path)
    with open(dyn_config_path, "w") as f:
        json.dump(config_data, f, indent=4)

# Reset config to default
def reset_to_default():
    dyn_config_path = get_resource_path("config/initialization.json")
    with open(dyn_config_path) as f:
        default_data = json.load(f)
    save_config(default_data, dyn_config_path)
    st.session_state["reset_triggered"] = True


# Reset config to default
def set_new_default():
    # Path to current user-modified config
    current_config_path = get_resource_path("config/initialization.json")
    
    # Path to fallback (default) config that we will overwrite
    fallback_config_path = get_resource_path("config/fallback_config_files/initialization.json")

    # Load the current config data
    with open(current_config_path, 'r', encoding='utf-8') as f:
        user_config_data = json.load(f)

    # Write it to the fallback config location
    with open(fallback_config_path, 'w', encoding='utf-8') as f:
        json.dump(user_config_data, f, indent=4)

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

    reset_dynsaties, delete_all_dynasties, set_new_dynasties = st.columns(3)
    with reset_dynsaties:
        if st.button("🔄 Reset Dynasties", disabled=disabled):
            reset_to_default()
            # If reset was triggered, reload config and clear flag
            if st.session_state.get("reset_triggered", False):
                config = load_config("config/fallback_config_files/initialization.json")
                save_config(config, "config/initialization.json")
                st.success("Configuration reset to default.")
                st.session_state["reset_triggered"] = False
            else:
                config = load_config("config/initialization.json")
    with set_new_dynasties:
        if st.button("🔄 Set New Fallback Dynasties", disabled=disabled):
            set_new_default()
            st.success("New default dynasties set.")
    with delete_all_dynasties:
        if st.button("❌ Delete All Dynasties", disabled=disabled):
            config['dynasties'].clear()
            save_config(config, "config/initialization.json")
            st.rerun()
            st.success("All Dynasties Deleted.")
            

    # Split the layout into 3 horizontal columns
    col1, col2 = st.columns(2)

    st.header(body="Global Simulation Settings", divider="grey")
    # Text inputs inside columns
    with col1:
        min_year = st.text_input("Start Year of Simulation (script date)", value=str(config.get("minYear", "0")), key="min_year_input")
    with col2:
        max_year = st.text_input("End Year of Simulation (script date)", value=str(config.get("maxYear", "1000")), key="max_year_input")
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
    succession_options = [law.value for law in SuccessionType]
    # Dynamically render dynasty accordions
    i = 0
    
    st.header(body="Add New Dynasty", divider="grey")
    with st.expander("➕ Add New Dynasty"):
        with st.form(key="add_dynasty_form"):
            new_name = st.text_input(help="The localization that will be displayed in-game for the dynasty name",label="Dynasty Name", disabled=disabled)
            new_motto = st.text_input(help="The localization that will be displayed in-game for the dynasty motto",label="Motto", disabled=disabled)
            new_succession = st.selectbox(help="The succession law which is used to determine who will be the next ruler, with the possible rulers determined by the \"Gender Law\"",label="Succession", options=succession_options, disabled=disabled)
            new_id = st.text_input(help="The dynasty ID that will be defined in script",label="Dynasty ID", disabled=disabled)
            new_house = st.checkbox(help="Whether this dynasty is a cadet branch of an existing dynasty in the history files",label="Is House?", value=False, disabled=disabled)
            new_faith = st.text_input(help="The religion ID that will be used when defining the dynasty and generating the characters",label="Faith ID", disabled=disabled)
            new_culture = st.text_input(help="The culture ID that will be used when defining the dynasty and generating the characters",label="Culture ID", disabled=disabled)
            new_gender_law = st.selectbox(help="The gender law which is applied to this dynasty.\n\nAGNATIC == Male Only\n\nAGNATIC_COGNATIC == Male Preference\n\nABSOLUTE_COGNATIC == Equal\n\nENATIC_COGNATIC == Female Preference\n\nENATIC == Female Only",label="Gender Law", options=gender_options, disabled=disabled)
            new_year = st.number_input(help="The birth year of the first character of this dynasty, essentially denoting when the dynasty starts",label="Progenitor Birth Year", value=6000, step=1, disabled=disabled)
            new_firstCousinMarraige = st.checkbox(help="Whether a dynasty will allow first cousin marraiges",label="First Cousin Marriage",value=False)
            # Optional field: Numenor Blood Tier
            numenor_blood = st.number_input("Numenor Blood Tier (Optional - Set value to 0 for it to NOT be included)", min_value=0, value=0, max_value=10, help="Set value to 0 if you do NOT want a dynasty to have numenorean blood", disabled=disabled)
            
            # Optional field: Languages list
            language_input = st.text_area("Languages (Optional - Format: language_id,startYear,endYear)", help="Languages that characters will learn in history.\n\nFormat: LANGUAGE_ID,START_YEAR,END_YEAR\n\nExample: language_sindarin, 6033,7033\n\nThe above example will give characters in this dynasty the sindarin language between the 6033 and 7033 dates.", disabled=disabled)

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
                "allowFirstCousinMarriage": new_firstCousinMarraige,
                "nameInheritance": {
                    "grandparentNameInheritanceChance": 0.05,
                    "parentNameInheritanceChance": 0.05,
                    "noNameInheritanceChance": 0.9
                }
            }

            if numenor_blood > 0 and numenor_blood < 11:
                try:
                    new_dynasty["numenorBloodTier"] = int(numenor_blood)
                except ValueError:
                    st.warning("Numenor Blood Tier must be an integer if set and must be between (exclusive) 0 - 10 (inclusive).")
            else:
                new_dynasty.pop("numenorBloodTier", None)  # Remove if 0 or not set

            # Parse and add languages
            if language_input.strip():
                lines = language_input.strip().splitlines()
                parsed_languages = []
                for line in lines:
                    parts = [x.strip() for x in line.split(",")]
                    if len(parts) == 3:
                        parsed_languages.append(f"{parts[0]},{parts[1]},{parts[2]}")
                    else:
                        st.warning(f"Invalid language entry: {line}")
                if parsed_languages:
                    new_dynasty["languages"] = parsed_languages

            config['dynasties'].append(new_dynasty)
            save_config(config, "config/initialization.json")
            st.rerun()

    st.header(body="Current Dynasties in Simulation", divider="grey")
    config['dynasties'].sort(key=lambda d: d['dynastyID'].lower())
    for i, dynasty in enumerate(config['dynasties']):
        current_gender_law = dynasty.get('gender_law', gender_options[0])
        current_succession_law = dynasty.get('succession', succession_options[0])
        
        # Create two columns for header: Dynasty title and Delete button
        col1, col2 = st.columns([11, 1])  # Adjust widths as needed

        with col1:
            st.markdown(f"#### Dynasty: {dynasty['dynastyID']}")
        with col2:
            if st.button(help=f"Delete {dynasty['dynastyID']}", label="❌", key=f"delete_dynasty_{i}", disabled=disabled):
                config['dynasties'].remove(dynasty)
                save_config(config, "config/initialization.json")
                st.rerun()

        with st.expander("Edit Dynasty Details", expanded=False):
            dynasty['dynastyName'] = st.text_input(help="The localization that will be displayed in-game for the dynasty name",label="Dynasty Name", value=dynasty["dynastyName"], key=f"name_{i}", disabled=disabled)
            dynasty['dynastyMotto'] = st.text_input(help="The localization that will be displayed in-game for the dynasty motto",label="Dynasty Motto", value=dynasty["dynastyMotto"], key=f"motto_{i}", disabled=disabled)
            dynasty['succession'] = st.selectbox(help="The succession law which is used to determine who will be the next ruler, with the possible rulers determined by the \"Gender Law\"",label="Succession", options=succession_options, index=succession_options.index(current_succession_law), key=f"succession_{i}", disabled=disabled)
            dynasty['dynastyID'] = st.text_input(help="The dynasty ID that will be defined in script",label="Dynasty ID", value=dynasty["dynastyID"], key=f"id_{i}", disabled=disabled)
            dynasty['isHouse'] = st.checkbox(help="Whether this dynasty is a cadet branch of an existing dynasty in the history files",label="Is House?", value=dynasty["isHouse"], key=f"house_{i}", disabled=disabled)
            dynasty['faithID'] = st.text_input(help="The religion ID that will be used when defining the dynasty and generating the characters",label="Faith ID", value=dynasty["faithID"], key=f"faith_{i}", disabled=disabled)
            dynasty['cultureID'] = st.text_input(help="The culture ID that will be used when defining the dynasty and generating the characters",label="Culture ID", value=dynasty["cultureID"], key=f"culture_{i}", disabled=disabled)
            dynasty["gender_law"] = st.selectbox(help="The gender law which is applied to this dynasty.\n\nAGNATIC == Male Only\n\nAGNATIC_COGNATIC == Male Preference\n\nABSOLUTE_COGNATIC == Equal\n\nENATIC_COGNATIC == Female Preference\n\nENATIC == Female Only",label="Gender Law", options=gender_options, index=gender_options.index(current_gender_law), key=f"gender_{i}", disabled=disabled)
            dynasty['progenitorMaleBirthYear'] = st.number_input(help="The birth year of the first character of this dynasty, essentially denoting when the dynasty starts",label="Progenitor Birth Year", value=dynasty["progenitorMaleBirthYear"], step=1, key=f"birth_year_{i}", disabled=disabled)
            dynasty['allowFirstCousinMarriage'] = st.checkbox(help="Whether a dynasty will allow first cousin marraiges",label="First Cousin Marriage",key=f"first_cousin_marriage_{i}",value=dynasty['allowFirstCousinMarriage'])
            # --- Numenor Blood Tier Editing ---
            st.markdown("**Numenor Blood Tier**")

            # If the field doesn't exist, show a way to add it
            if "numenorBloodTier" not in dynasty:
                add_key = f"add_blood_tier_{i}_clicked"
                if st.button("➕ Add Numenor Blood Tier", key=f"add_blood_tier_{i}", disabled=disabled):
                    st.session_state[add_key] = True
                    dynasty["numenorBloodTier"] = 1  # Default value

                # Show the slider if it's in the config or the session state tracked the button press
                if "numenorBloodTier" in dynasty or st.session_state.get(add_key, False):
                    tier = dynasty.get("numenorBloodTier", 1)
                    new_tier = st.slider(
                        help="The numenorean blood tier of this dynasty's progenitor",
                        label="Numenor Blood Tier",
                        min_value=1, max_value=10,
                        value=int(tier),
                        key=f"blood_tier_{i}",
                        disabled=disabled
                    )
                    dynasty["numenorBloodTier"] = new_tier
                    if st.button("❌ Remove Blood Tier", key=f"remove_blood_tier_{i}", disabled=disabled):
                        dynasty.pop("numenorBloodTier", None)
                        st.session_state.pop(add_key, None)
                        save_config(config, "config/initialization.json")
                        st.rerun()
            else:
                tier = dynasty.get("numenorBloodTier", 0)
                new_tier = st.slider(help="The numenorean blood tier of this dyansties progenitor", label="Numenor Blood Tier", min_value=1, max_value=10, value=int(tier), key=f"blood_tier_{i}", disabled=disabled)
                dynasty["numenorBloodTier"] = new_tier
                if st.button("❌ Remove Blood Tier", key=f"remove_blood_tier_{i}", disabled=disabled):
                    del dynasty["numenorBloodTier"]
                    save_config(config, "config/initialization.json")
                    st.rerun()
            
            # --- Languages Editing Section ---
            st.markdown("**Languages**")

            # Ensure a stable key prefix per dynasty
            lang_key_prefix = f"lang_{i}_"

            # Initialize language list if not present in both config and session state
            if "languages" not in dynasty:
                dynasty["languages"] = []

            session_key = f"{lang_key_prefix}list"
            if session_key not in st.session_state:
                st.session_state[session_key] = dynasty["languages"]

            # Store edited languages
            edited_languages = []

            for lang_index, lang_entry in enumerate(st.session_state[session_key]):
                try:
                    lang_id, start, end = lang_entry.split(",")
                    start = int(start)
                    end = int(end)
                except ValueError:
                    lang_id, start, end = "", 0, 0

                lang_cols = st.columns([4, 2, 2, 1])
                with lang_cols[0]:
                    new_id = st.text_input("Language", value=lang_id, key=f"{lang_key_prefix}id_{lang_index}", disabled=disabled)
                with lang_cols[1]:
                    new_start = st.number_input("Start", value=start, key=f"{lang_key_prefix}start_{lang_index}", step=1, disabled=disabled)
                with lang_cols[2]:
                    new_end = st.number_input("End", value=end, key=f"{lang_key_prefix}end_{lang_index}", step=1, disabled=disabled)
                with lang_cols[3]:
                    if st.button("❌", key=f"{lang_key_prefix}delete_{lang_index}", help="Remove this language", disabled=disabled):
                        st.session_state[session_key].pop(lang_index)
                        st.rerun()

                if new_id:
                    edited_languages.append(f"{new_id},{int(new_start)},{int(new_end)}")

            # Add new language entry
            if st.button("➕ Add Language", key=f"{lang_key_prefix}add", disabled=disabled):
                st.session_state[session_key].append("new_lang,0,0")
                st.rerun()

            # Save the edited list back to dynasty config
            if edited_languages:
                dynasty["languages"] = edited_languages
            elif "languages" in dynasty:
                del dynasty["languages"]

    st.header(body="Save Dynasty Changes", divider="grey")
    if st.button("💾 Save Dynasty Changes", disabled=disabled):
        save_config(config, "config/initialization.json")
        st.success("Configuration saved.")
    
    st.header(body="Run Simulation", divider="grey")
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

    event_options = [event.value for event in EventType] 
    
    with st.expander("➕ Add New Event"):
        with st.form(key="add_event"):
            new_eventID = st.selectbox(help="The internal event ID which will be used to determine death reason of a character",label="Event ID", options=event_options, key=f"eventID", disabled=disabled)
            new_startYear = st.number_input(help="The date at which this event STARTS to apply to the characters",label="Start Year", value=6000, step=1, disabled=disabled)
            new_endYear = st.number_input(help="The date at which this event STOPS applying to the characters",label="End Year", value=6500, step=1, disabled=disabled)
            new_deathReason = st.text_input(help="The id of the death reason applied to the character in history\n\nAn example of a death id would be \"death_plague\" for a plague event",label="Death Reason ID", disabled=disabled)
            new_deathMultiplier = st.number_input(help="The increased chance of a character dying during this event",label="Lethality Factor", min_value=0.0, max_value=1.0, value=0.5, step=0.1, disabled=disabled)
            new_characterAgeStart = st.number_input(help="The minimum age at which this event can start affecting characters",label="Minimum Character Age", min_value=0, max_value=300, value=0, step=1, disabled=disabled)
            new_characterAgeEnd = st.number_input(help="The maximum age at which this event can start affecting characters",label="Maximum Character Age", min_value=0, max_value=300, value=60, step=1, disabled=disabled)
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
        current_event = event.get('eventID', event_options[0])

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
            new_eventID = st.selectbox(help="The internal event ID which will be used to determine death reason of a character",label="Event ID", options=event_options, index=event_options.index(current_event), key=f"eventID_{i}", disabled=disabled)
            event['startYear'] = st.number_input(help="The date at which this event STARTS to apply to the characters",label="Start Year", value=event["startYear"], step=1, key=f"startYear_{i}", disabled=disabled)
            event['endYear'] = st.number_input(help="The date at which this event STOPS applying to the characters",label="End Year", value=event["endYear"], step=1, key=f"endYear_{i}", disabled=disabled)
            event['deathReason'] = st.text_input(help="The id of the death reason applied to the character in history",label="Death Reason", value=event["deathReason"], key=f"deathReason_{i}", disabled=disabled)
            event['deathMultiplier'] = st.number_input(help="The increased chance of a character dying during this event",label="Lethality Factor", min_value=0.0, max_value=1.0, value=event["deathMultiplier"], step=0.1, key=f"deathMultiplier_{i}", disabled=disabled)
            event['characterAgeStart'] = st.number_input(help="The minimum age at which this event can start affecting characters",label="Character Minimum Age", min_value=0, max_value=120, value=event["characterAgeStart"], step=1, key=f"characterAgeStart_{i}", disabled=disabled)
            event["characterAgeEnd"] = st.number_input(help="The maximum age at which this event can start affecting characters",label="Character Maximum Age", min_value=0, max_value=120, value=event["characterAgeEnd"], step=1, key=f"characterAgeEnd_{i}", disabled=disabled)

    # Save updated values
    if st.button("💾 Save Event Changes", disabled=disabled):
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

    # with st.expander("Edit Life Cycle Modifier Details", expanded=False):
    config['marriageMaxAgeDifference'] = st.number_input(help="Determines what the maximum difference can be between 2 characters. As an example, if the maximum difference is 5, the largest marriage age difference will be 25 to 30.",label="Maximum Difference in Age Between Spouses", min_value=0, max_value=30, value=config["marriageMaxAgeDifference"], key=f"marriageMaxAgeDifference", disabled=disabled)
    config['maximumNumberOfChildren'] = st.number_input(help="Determines the maximum number of children any female character can have.",label="Maximum Number of Children", value=config["maximumNumberOfChildren"], min_value=1, max_value=10, step=1, key=f"maximumNumberOfChildren", disabled=disabled)
    config['minimumYearsBetweenChildren'] = st.number_input(help="Determines the number of years enforced between the births of siblings.",label="Minimum Years Between Children", min_value=1, max_value=10, value=config["minimumYearsBetweenChildren"], step=1, key=f"minimumYearsBetweenChildren", disabled=disabled)
    config['bastardyChanceMale'] = st.number_input(help="The chance for a male child to be born as a bastard",label="Chance for Male Bastards", format="%0.4f", min_value=0.0000, max_value=1.0000, value=config["bastardyChanceMale"], step=0.0005, key=f"bastardyChanceMale", disabled=disabled)
    config['bastardyChanceFemale'] = st.number_input(help="The chance for a female child to be born as a bastard",label="Chance for Female Bastards", format="%0.4f", min_value=0.0000, max_value=1.0000, value=config["bastardyChanceFemale"], step=0.0005, key=f"bastardyChanceFemale", disabled=disabled)
        
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

    # Slider for adjusting mortality rates
    Multiplier = st.slider(
        "Adjust Desperation Marriage Rate Multiplier",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.01
    )
    
    # Age range for the data
    ages = list(range(len(desperationMarriageRates)))

    # Apply multiplier
    adjustedRates = [rate * Multiplier for rate in desperationMarriageRates]


    # Plot desperation marriage rates
    plt.figure(figsize=(12, 6))
    plt.plot(ages, adjustedRates, label='Desperation Marriage Rate', color='red')
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