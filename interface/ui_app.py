import base64
import logging
from pathlib import Path
import streamlit as st
import sys
import os
import matplotlib.pyplot as plt
import json
from enum import Enum

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import run_main

############################
# Enums for Config
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

# Pre-calculate enum lists for selectboxes
EVENT_OPTIONS = [e.value for e in EventType]
GENDER_OPTIONS = [g.value for g in GenderLaw]
SUCCESSION_OPTIONS = [s.value for s in SuccessionType]

############################
# Config File Utilities
############################

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.abspath(os.path.join(base_path, '..', relative_path))

def load_config(config_path):
    """Loads a JSON config file from the resource path."""
    full_path = get_resource_path(config_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config_data, config_path):
    """Saves a dictionary as JSON to the resource path."""
    full_path = get_resource_path(config_path)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)

def reset_config(config_key, config_path, fallback_path):
    """Resets a config in session_state to its fallback default."""
    try:
        default_data = load_config(fallback_path)
        save_config(default_data, config_path)
        st.session_state[config_key] = default_data
        st.success("Configuration reset to default.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to reset config: {e}")

def set_new_default(config_path, fallback_path):
    """Overwrites the fallback file with the current config."""
    try:
        current_data = load_config(config_path)
        save_config(current_data, fallback_path)
        st.success("New fallback configuration saved.")
    except Exception as e:
        st.error(f"Failed to set new default: {e}")

############################
# Reusable Form Renderers
############################

def render_dynasty_fields(dynasty_data, key_prefix, disabled=False):
    """
    Renders all widgets for a dynasty form (either new or edit).
    If dynasty_data is None, renders an empty "new" form.
    Otherwise, populates widgets with data from the dynasty_data dict.
    """
    
    # Helper to get existing value or default
    def get_val(key, default=""):
        if dynasty_data:
            return dynasty_data.get(key, default)
        return default

    # Use a dictionary to store form data
    data = {}

    data['dynastyName'] = st.text_input(
        label="Dynasty Name",
        value=get_val("dynastyName"),
        help="The localization that will be displayed in-game for the dynasty name",
        key=f"{key_prefix}_name",
        disabled=disabled
    )
    data['dynastyMotto'] = st.text_input(
        label="Dynasty Motto",
        value=get_val("dynastyMotto"),
        help="The localization that will be displayed in-game for the dynasty motto",
        key=f"{key_prefix}_motto",
        disabled=disabled
    )
    data['succession'] = st.selectbox(
        label="Succession",
        options=SUCCESSION_OPTIONS,
        index=SUCCESSION_OPTIONS.index(get_val('succession', SUCCESSION_OPTIONS[0])),
        help="The succession law which is used to determine who will be the next ruler, with the possible rulers determined by the \"Gender Law\"",
        key=f"{key_prefix}_succession",
        disabled=disabled
    )
    data['dynastyID'] = st.text_input(
        label="Dynasty ID",
        value=get_val("dynastyID"),
        help="The dynasty ID that will be defined in script",
        key=f"{key_prefix}_id",
        disabled=disabled
    )
    data['isHouse'] = st.checkbox(
        label="Is House?",
        value=get_val("isHouse", False),
        help="Whether this dynasty is a cadet branch of an existing dynasty in the history files",
        key=f"{key_prefix}_house",
        disabled=disabled
    )
    data['faithID'] = st.text_input(
        label="Faith ID",
        value=get_val("faithID"),
        help="The religion ID that will be used when defining the dynasty and generating the characters",
        key=f"{key_prefix}_faith",
        disabled=disabled
    )
    data['cultureID'] = st.text_input(
        label="Culture ID",
        value=get_val("cultureID"),
        help="The culture ID that will be used when defining the dynasty and generating the characters",
        key=f"{key_prefix}_culture",
        disabled=disabled
    )
    data["gender_law"] = st.selectbox(
        label="Gender Law",
        options=GENDER_OPTIONS,
        index=GENDER_OPTIONS.index(get_val('gender_law', GENDER_OPTIONS[0])),
        help="The gender law which is applied to this dynasty.\n\nAGNATIC == Male Only\n\nAGNATIC_COGNATIC == Male Preference\n\nABSOLUTE_COGNATIC == Equal\n\nENATIC_COGNATIC == Female Preference\n\nENATIC == Female Only",
        key=f"{key_prefix}_gender",
        disabled=disabled
    )
    data['progenitorMaleBirthYear'] = st.number_input(
        label="Progenitor Birth Year",
        value=get_val("progenitorMaleBirthYear", 6000),
        step=1,
        help="The birth year of the first character of this dynasty, essentially denoting when the dynasty starts",
        key=f"{key_prefix}_birth_year",
        disabled=disabled
    )
    data['allowFirstCousinMarriage'] = st.checkbox(
        label="First Cousin Marriage",
        value=get_val("allowFirstCousinMarriage", False),
        help="Whether a dynasty will allow first cousin marriages",
        key=f"{key_prefix}_first_cousin_marriage",
        disabled=disabled
    )
    data['prioritiseLowbornMarraige'] = st.checkbox(
        label="Prioritise Lowborn Marriage",
        value=get_val("prioritiseLowbornMarraige", False),
        help="Whether a dynasty will prioritise lowborn marriages over characters with dynasties",
        key=f"{key_prefix}_prioritise_lowborn_marriage",
        disabled=disabled
    )

    # --- Numenor Blood Tier Editing ---
    st.markdown("**Numenor Blood Tier**", help="Set ***value to 0*** if you do ***NOT*** want a dynasty to have numenorean blood")
    
    # This logic is for "edit" forms
    if dynasty_data:
        if "numenorBloodTier" not in dynasty_data:
            if st.button("➕ Add Numenor Blood Tier", key=f"{key_prefix}_add_blood_tier", disabled=disabled):
                dynasty_data["numenorBloodTier"] = 1  # Default value
                st.rerun()
        else:
            tier = dynasty_data.get("numenorBloodTier", 1)
            new_tier = st.slider(
                label="Numenor Blood Tier",
                min_value=1, max_value=10,
                value=int(tier),
                help="The numenorean blood tier of this dynasty's progenitor",
                key=f"{key_prefix}_blood_tier",
                disabled=disabled
            )
            dynasty_data["numenorBloodTier"] = new_tier
            if st.button("❌ Remove Blood Tier", key=f"{key_prefix}_remove_blood_tier", disabled=disabled):
                del dynasty_data["numenorBloodTier"]
                st.rerun()
    # This logic is for "new" forms
    else:
        data["numenorBloodTier"] = st.number_input(
            "Numenor Blood Tier (Optional - Set value to 0 for it to NOT be included)",
            min_value=0, value=0, max_value=10,
            help="Set value to 0 if you do NOT want a dynasty to have numenorean blood",
            key=f"{key_prefix}_blood_tier",
            disabled=disabled
        )

    # --- Languages Editing Section ---
    st.markdown("**Languages**", help="Languages that characters will learn in history.\n\nFormat: LANGUAGE_ID,START_YEAR,END_YEAR\n\nExample: language_sindarin, 6033,7033")
    
    # This logic is for "edit" forms
    if dynasty_data:
        if "languages" not in dynasty_data:
            dynasty_data["languages"] = []

        edited_languages = []
        for lang_index, lang_entry in enumerate(dynasty_data["languages"]):
            try:
                lang_id, start, end = lang_entry.split(",")
                start = int(start)
                end = int(end)
            except ValueError:
                lang_id, start, end = "", 0, 0

            lang_cols = st.columns([4, 2, 2, 1])
            new_id = lang_cols[0].text_input("Language", value=lang_id, key=f"{key_prefix}_lang_id_{lang_index}", disabled=disabled)
            new_start = lang_cols[1].number_input("Start", value=start, key=f"{key_prefix}_lang_start_{lang_index}", step=1, disabled=disabled)
            new_end = lang_cols[2].number_input("End", value=end, key=f"{key_prefix}_lang_end_{lang_index}", step=1, disabled=disabled)
            
            if lang_cols[3].button("❌", key=f"{key_prefix}_lang_delete_{lang_index}", help="Remove this language", disabled=disabled):
                dynasty_data["languages"].pop(lang_index)
                st.rerun()
            
            if new_id:
                edited_languages.append(f"{new_id},{int(new_start)},{int(new_end)}")

        if st.button("➕ Add Language", key=f"{key_prefix}_lang_add", disabled=disabled):
            dynasty_data["languages"].append("new_lang,0,0")
            st.rerun()
        
        # Save the edited list back to dynasty config
        dynasty_data["languages"] = edited_languages if edited_languages else []

    # This logic is for "new" forms
    else:
        data["languages_raw"] = st.text_area(
            "Languages (Optional - Format: language_id,startYear,endYear)",
            help="One entry per line. Example: language_sindarin,6033,7033",
            key=f"{key_prefix}_languages",
            disabled=disabled
        )

    # For "edit" forms, we're modifying the dict in-place.
    if dynasty_data:
        # Update the dynasty dict with the simple values
        dynasty_data.update(data)
        return None # Data is modified in-place
    
    # For "new" forms, we return the collected data
    return data


def render_event_fields(event_data, key_prefix, disabled=False):
    """
    Renders all widgets for an event form (either new or edit).
    If event_data is None, renders an empty "new" form.
    Otherwise, populates widgets with data from the event_data dict.
    """
    
    def get_val(key, default=""):
        if event_data:
            return event_data.get(key, default)
        
        # Defaults for "new" form
        if key == "startYear": return 6000
        if key == "endYear": return 6500
        if key == "deathMultiplier": return 0.5
        if key == "characterAgeStart": return 0
        if key == "characterAgeEnd": return 60
        return default

    data = {}
    
    data['eventID'] = st.selectbox(
        label="Event ID",
        options=EVENT_OPTIONS,
        index=EVENT_OPTIONS.index(get_val('eventID', EVENT_OPTIONS[0])),
        help="The internal event ID which will be used to determine death reason of a character",
        key=f"{key_prefix}_eventID",
        disabled=disabled
    )
    data['startYear'] = st.number_input(
        label="Start Year",
        value=get_val("startYear"),
        step=1,
        help="The date at which this event STARTS to apply to the characters",
        key=f"{key_prefix}_startYear",
        disabled=disabled
    )
    data['endYear'] = st.number_input(
        label="End Year",
        value=get_val("endYear"),
        step=1,
        help="The date at which this event STOPS applying to the characters",
        key=f"{key_prefix}_endYear",
        disabled=disabled
    )
    data['deathReason'] = st.text_input(
        label="Death Reason ID",
        value=get_val("deathReason"),
        help="The id of the death reason applied to the character in history\n\nAn example of a death id would be \"death_plague\" for a plague event",
        key=f"{key_prefix}_deathReason",
        disabled=disabled
    )
    data['deathMultiplier'] = st.number_input(
        label="Lethality Factor",
        min_value=0.0, max_value=1.0,
        value=get_val("deathMultiplier"),
        step=0.1,
        help="The increased chance of a character dying during this event",
        key=f"{key_prefix}_deathMultiplier",
        disabled=disabled
    )
    data['characterAgeStart'] = st.number_input(
        label="Minimum Character Age",
        min_value=0, max_value=300,
        value=get_val("characterAgeStart"),
        step=1,
        help="The minimum age at which this event can start affecting characters",
        key=f"{key_prefix}_characterAgeStart",
        disabled=disabled
    )
    data['characterAgeEnd'] = st.number_input(
        label="Maximum Character Age",
        min_value=0, max_value=300,
        value=get_val("characterAgeEnd"),
        step=1,
        help="The maximum age at which this event can start affecting characters",
        key=f"{key_prefix}_characterAgeEnd",
        disabled=disabled
    )

    # For "edit" forms, modify in-place
    if event_data:
        event_data.update(data)
        return None
    
    # For "new" forms, return the data
    return data

############################
# Tab Display Functions
############################

def display_dynasty_config(config):
    """Renders the 'Dynasty Settings' tab using the provided config dict."""
    st.title("CK3 Character History Generator")
    
    disabled = not st.session_state.get("configs_loaded", False)
    
    CONFIG_PATH = "config/initialization.json"
    FALLBACK_PATH = "config/fallback_config_files/initialization.json"

    reset_dynasties, delete_all_dynasties, set_new_dynasties = st.columns(3)
    reset_dynasties.button(
        "🔄 Reset Dynasties",
        on_click=reset_config,
        args=("init_config", CONFIG_PATH, FALLBACK_PATH),
        disabled=disabled
    )
    set_new_dynasties.button(
        "🔄 Set New Fallback Dynasties",
        on_click=set_new_default,
        args=(CONFIG_PATH, FALLBACK_PATH),
        disabled=disabled
    )
    if delete_all_dynasties.button("❌ Delete All Dynasties", disabled=disabled):
        config['dynasties'].clear()
        save_config(config, CONFIG_PATH)
        st.rerun()

    st.header(body="Global Simulation Settings", divider="grey")
    with st.form(key="global_settings_form"):
        col1, col2 = st.columns(2)
        min_year = col1.number_input(
            "Start Year of Simulation (script date)",
            value=config.get("minYear", 0),
            step=1,
            key="min_year_input"
        )
        max_year = col2.number_input(
            "End Year of Simulation (script date)",
            value=config.get("maxYear", 1000),
            step=1,
            key="max_year_input"
        )
        max_generations = st.slider(
            "Maximum Number of Generations",
            min_value=1, max_value=200,
            value=config.get('generationMax', 10),
            step=1,
            key="max_gen_characters"
        )
        
        if st.form_submit_button("💾 Save Global Settings", disabled=disabled):
            try:
                config["minYear"] = int(min_year)
                config["maxYear"] = int(max_year)
                config["generationMax"] = int(max_generations)
                save_config(config, CONFIG_PATH)
                st.success("Global settings saved successfully!")
            except ValueError:
                st.error("All inputs must be valid integers.")

    st.header(body="Add New Dynasty", divider="grey")
    with st.expander("➕ Add New Dynasty"):
        with st.form(key="add_dynasty_form"):
            new_dynasty_data = render_dynasty_fields(None, "new_dynasty", disabled)
            submit = st.form_submit_button("Add Dynasty", disabled=disabled)

            if submit:
                # Process the "new" form data
                new_dynasty = new_dynasty_data.copy()
                
                # Handle Numenor Blood
                numenor_blood = new_dynasty.pop("numenorBloodTier", 0)
                if numenor_blood > 0:
                    new_dynasty["numenorBloodTier"] = int(numenor_blood)

                # Handle Languages
                language_input = new_dynasty.pop("languages_raw", "")
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
                
                # Add default name inheritance
                new_dynasty["nameInheritance"] = {
                    "grandparentNameInheritanceChance": 0.05,
                    "parentNameInheritanceChance": 0.05,
                    "noNameInheritanceChance": 0.9
                }
                
                config['dynasties'].append(new_dynasty)
                save_config(config, CONFIG_PATH)
                st.rerun()

    st.header(body="Current Dynasties in Simulation", divider="grey")
    config['dynasties'].sort(key=lambda d: d.get('dynastyID', '').lower())
    
    for i, dynasty in enumerate(config['dynasties']):
        col1, col2 = st.columns([11, 1])
        col1.markdown(f"#### Dynasty: {dynasty.get('dynastyID', 'Unnamed')}")
        if col2.button("❌", key=f"delete_dynasty_{i}", help=f"Delete {dynasty.get('dynastyID', 'this dynasty')}", disabled=disabled):
            config['dynasties'].pop(i)
            save_config(config, CONFIG_PATH)
            st.rerun()

        with st.expander("Edit Dynasty Details", expanded=False):
            # Render the edit form. Changes are made directly to the `dynasty` dict.
            render_dynasty_fields(dynasty, f"dynasty_{i}", disabled)

    if st.button("💾 Save All Dynasty Changes", disabled=disabled):
        save_config(config, CONFIG_PATH)
        st.success("Dynasty changes saved.")

    st.header(body="Run Simulation", divider="grey")
    if st.button("Run Simulation", disabled=disabled):
        with st.spinner("Running simulation... This may take a moment."):
            try:
                run_main()
                st.success("Simulation complete! Check the 'Dynasty Trees' tab for results.")
            except Exception as e:
                st.error(f"An error occurred during simulation: {e}")
                logging.exception("Simulation run failed")

def display_event_config(config):
    """Renders the 'Negative Events' tab using the provided config dict."""
    st.title("CK3 Character History Generator")
    st.subheader("📜 Negative Events Impacting Death Rates")
    
    disabled = not st.session_state.get("configs_loaded", False)

    CONFIG_PATH = "config/initialization.json"
    FALLBACK_PATH = "config/fallback_config_files/initialization.json"

    if st.button("🔄 Reset Events", disabled=disabled):
        # This will reset the *entire* initialization.json
        reset_config("init_config", CONFIG_PATH, FALLBACK_PATH)
        st.warning("Events reset. Note: This resets Dynasty settings as well.")

    with st.expander("➕ Add New Event"):
        with st.form(key="add_event_form"):
            new_event_data = render_event_fields(None, "new_event", disabled)
            submit = st.form_submit_button("Add Event", disabled=disabled)

            if submit:
                config['events'].append(new_event_data)
                save_config(config, CONFIG_PATH)
                st.rerun()

    config['events'].sort(key=lambda d: d.get('eventID', '').lower())
    for i, event in enumerate(config['events']):
        col1, col2 = st.columns([11, 1])
        col1.markdown(f"#### Event: {event.get('eventID', 'Unnamed')}")
        if col2.button("❌", key=f"delete_event_{i}", help=f"Delete {event.get('eventID', 'this event')}", disabled=disabled):
            config['events'].pop(i)
            save_config(config, CONFIG_PATH)
            st.rerun()
            
        with st.expander("Edit Event Details", expanded=False):
            # Render the edit form. Changes are made directly to the `event` dict.
            render_event_fields(event, f"event_{i}", disabled)

    if st.button("💾 Save Event Changes", disabled=disabled):
        save_config(config, CONFIG_PATH)
        st.success("Event changes saved.")

def display_life_stage_config(config):
    """Renders the 'Life Cycle Modifiers' tab using the provided config dict."""
    st.title("CK3 Character History Generator")
    st.subheader("💉 Life Cycle Modifiers")
    
    disabled = not st.session_state.get("configs_loaded", False)
    
    CONFIG_PATH = "config/life_stages.json"
    FALLBACK_PATH = "config/fallback_config_files/life_stages.json"

    st.button(
        "🔄 Reset Life Cycle Modifiers",
        on_click=reset_config,
        args=("life_config", CONFIG_PATH, FALLBACK_PATH),
        disabled=disabled
    )

    # --- Simple Modifiers ---
    config['marriageMaxAgeDifference'] = st.number_input(
        label="Maximum Difference in Age Between Spouses",
        min_value=0, max_value=30,
        value=config.get("marriageMaxAgeDifference", 10),
        help="Determines what the maximum difference can be between 2 characters. As an example, if the maximum difference is 5, the largest marriage age difference will be 25 to 30.",
        key="marriageMaxAgeDifference",
        disabled=disabled
    )
    config['maximumNumberOfChildren'] = st.number_input(
        label="Maximum Number of Children",
        min_value=1, max_value=20,
        value=config.get("maximumNumberOfChildren", 8),
        step=1,
        help="Determines the maximum number of children any female character can have.",
        key="maximumNumberOfChildren",
        disabled=disabled
    )
    config['minimumYearsBetweenChildren'] = st.number_input(
        label="Minimum Years Between Children",
        min_value=1, max_value=10,
        value=config.get("minimumYearsBetweenChildren", 2),
        step=1,
        help="Determines the number of years enforced between the births of siblings.",
        key="minimumYearsBetweenChildren",
        disabled=disabled
    )
    config['bastardyChanceMale'] = st.number_input(
        label="Chance for Male Bastards",
        format="%0.4f", min_value=0.0000, max_value=1.0000,
        value=config.get("bastardyChanceMale", 0.001),
        step=0.0005,
        help="The chance for a male child to be born as a bastard",
        key="bastardyChanceMale",
        disabled=disabled
    )
    config['bastardyChanceFemale'] = st.number_input(
        label="Chance for Female Bastards",
        format="%0.4f", min_value=0.0000, max_value=1.0000,
        value=config.get("bastardyChanceFemale", 0.001),
        step=0.0005,
        help="The chance for a female child to be born as a bastard",
        key="bastardyChanceFemale",
        disabled=disabled
    )
        
    if st.button("💾 Save Life Cycle Modifier Changes", disabled=disabled):
        save_config(config, CONFIG_PATH)
        st.success("Life cycle modifiers saved.")
    
    # --- Plotting Sections ---
    # Pass the config dict to the plotting functions
    display_desperation_marriage_rates(config)
    display_mortality_rates(config)
    display_marriage_rates(config)
    display_fertility_rates(config)

############################
# Plotting Functions
############################

def display_desperation_marriage_rates(config):
    st.subheader("Desperation Marriage Rates")
    desperationMarriageRates = config.get('desperationMarriageRates', [0]*121)

    Multiplier = st.slider(
        "Adjust Desperation Marriage Rate Multiplier",
        min_value=0.0, max_value=2.0, value=1.0, step=0.01,
        key="desperation_slider"
    )
    
    ages = list(range(len(desperationMarriageRates)))
    adjustedRates = [min(rate * Multiplier, 1.0) for rate in desperationMarriageRates] # Cap at 1.0

    # --- NEW: Column Wrapper ---
    _fig_col, fig_col, _fig_col = st.columns([1, 4, 1])
    with fig_col:
        plt.figure(figsize=(10, 5)) # Kept smaller figsize
        plt.plot(ages, adjustedRates, label='Desperation Marriage Rate', color='red')
        plt.ylim(0.0, 1.0)
        plt.xlabel('Age')
        plt.ylabel('Rate')
        plt.title('Desperation Marriage Rates by Age')
        plt.grid(True)
        plt.legend()
        st.pyplot(plt.gcf())
        plt.clf()
    
def display_mortality_rates(config):
    st.subheader("Mortality Rates for Male/Female")
    mortalityRates = config.get('mortalityRates', {})
    maleMortalityRates = mortalityRates.get('Male', [0]*121)
    femaleMortalityRates = mortalityRates.get('Female', [0]*121)

    maleMultiplier = st.slider(
        "Adjust Male Mortality Rate Multiplier",
        min_value=0.0, max_value=2.0, value=1.0, step=0.01,
        key="male_mortality_slider"
    )
    adjustedMaleRates = [min(rate * maleMultiplier, 1.0) for rate in maleMortalityRates]

    # --- NEW: Column Wrapper ---
    _fig_col, fig_col, _fig_col = st.columns([1, 4, 1])
    with fig_col:
        plt.figure(figsize=(10, 5))
        plt.plot(range(len(adjustedMaleRates)), adjustedMaleRates, label='Male Mortality Rates', color='blue')
        plt.ylim(0.0, 1.0)
        plt.xlabel('Age')
        plt.ylabel('Rate')
        plt.title('Male Mortality Rate by Age (Adjusted)')
        plt.grid(True)
        plt.legend()
        st.pyplot(plt.gcf())
        plt.clf()
    
    femaleMultiplier = st.slider(
        "Adjust Female Mortality Rate Multiplier",
        min_value=0.0, max_value=2.0, value=1.0, step=0.01,
        key="female_mortality_slider"
    )
    adjustedFemaleRates = [min(rate * femaleMultiplier, 1.0) for rate in femaleMortalityRates]
    
    # --- NEW: Column Wrapper ---
    _fig_col, fig_col, _fig_col = st.columns([1, 4, 1])
    with fig_col:
        plt.figure(figsize=(10, 5))
        plt.plot(range(len(adjustedFemaleRates)), adjustedFemaleRates, label='Female Mortality Rate', color='red')
        plt.ylim(0.0, 1.0)
        plt.xlabel('Age')
        plt.ylabel('Rate')
        plt.title('Female Mortality Rate by Age')
        plt.grid(True)
        plt.legend()
        st.pyplot(plt.gcf())
        plt.clf()

def display_marriage_rates(config):
    st.subheader("Marriage Rates for Male/Female")
    marriageRates = config.get('marriageRates', {})
    maleMarriageRates = marriageRates.get('Male', [0]*121)
    femaleMarriageRates = marriageRates.get('Female', [0]*121)

    maleMultiplier = st.slider(
        "Adjust Male Marriage Rate Multiplier",
        min_value=0.0, max_value=2.0, value=1.0, step=0.01,
        key="male_marriage_slider"
    )
    adjustedMaleRates = [min(rate * maleMultiplier, 1.0) for rate in maleMarriageRates]

    # --- NEW: Column Wrapper ---
    _fig_col, fig_col, _fig_col = st.columns([1, 4, 1])
    with fig_col:
        plt.figure(figsize=(10, 5))
        plt.plot(range(len(adjustedMaleRates)), adjustedMaleRates, label='Male marriage Rates', color='blue')
        plt.ylim(0.0, 1.0)
        plt.xlabel('Age')
        plt.ylabel('Rate')
        plt.title('Male Marriage Rate by Age')
        plt.grid(True)
        plt.legend()
        st.pyplot(plt.gcf())
        plt.clf()
    
    femaleMultiplier = st.slider(
        "Adjust Female Marriage Rate Multiplier",
        min_value=0.0, max_value=2.0, value=1.0, step=0.01,
        key="female_marriage_slider"
    )
    adjustedFemaleRates = [min(rate * femaleMultiplier, 1.0) for rate in femaleMarriageRates]

    # --- NEW: Column Wrapper ---
    _fig_col, fig_col, _fig_col = st.columns([1, 4, 1])
    with fig_col:
        plt.figure(figsize=(10, 5))
        plt.plot(range(len(adjustedFemaleRates)), adjustedFemaleRates, label='Female marriage Rate', color='red')
        plt.ylim(0.0, 1.0)
        plt.xlabel('Age')
        plt.ylabel('Rate')
        plt.title('Female Marriage Rate by Age')
        plt.grid(True)
        plt.legend()
        st.pyplot(plt.gcf())
        plt.clf()

def display_fertility_rates(config):
    st.subheader("Fertility Rates for Male/Female")
    fertilityRates = config.get('fertilityRates', {})
    maleFertilityRates = fertilityRates.get('Male', [0]*121)
    femaleFertilityRates = fertilityRates.get('Female', [0]*121)

    maleMultiplier = st.slider(
        "Adjust Male Fertility Rate Multiplier",
        min_value=0.0, max_value=2.0, value=1.0, step=0.01,
        key="male_fertility_slider"
    )
    adjustedMaleRates = [min(rate * maleMultiplier, 1.0) for rate in maleFertilityRates]

    # --- NEW: Column Wrapper ---
    _fig_col, fig_col, _fig_col = st.columns([1, 4, 1])
    with fig_col:
        plt.figure(figsize=(10, 5))
        plt.plot(range(len(adjustedMaleRates)), adjustedMaleRates, label='Male fertility Rates', color='blue')
        plt.ylim(0.0, 1.0)
        plt.xlabel('Age')
        plt.ylabel('Rate')
        plt.title('Male fertility Rate by Age')
        plt.grid(True)
        plt.legend()
        st.pyplot(plt.gcf())
        plt.clf()
    
    femaleMultiplier = st.slider(
        "Adjust Female Fertility Rate Multiplier",
        min_value=0.0, max_value=2.0, value=1.0, step=0.01,
        key="female_fertility_slider"
    )
    adjustedFemaleRates = [min(rate * femaleMultiplier, 1.0) for rate in femaleFertilityRates]

    # --- NEW: Column Wrapper ---
    _fig_col, fig_col, _fig_col = st.columns([1, 4, 1])
    with fig_col:
        plt.figure(figsize=(10, 5))
        plt.plot(range(len(adjustedFemaleRates)), adjustedFemaleRates, label='Female fertility Rate', color='red')
        plt.ylim(0.0, 1.0)
        plt.xlabel('Age')
        plt.ylabel('Rate')
        plt.title('Female fertility Rate by Age')
        plt.grid(True)
        plt.legend()
        st.pyplot(plt.gcf())
        plt.clf()

############################
# Image Display Tab
############################

def display_generated_images(image_folder: str):
    st.title("CK3 Character History Generator")
    st.subheader("🧬 Generated Dynastic Trees")

    # Get all image files
    img_folder_path = get_resource_path(image_folder)
    image_paths = sorted(Path(img_folder_path).glob("family_tree_*.png"))

    if not image_paths:
        st.info("No dynasty tree images found. Run the simulation first.")
        return

    for image_path in image_paths:
        dynasty_id = image_path.stem.replace("family_tree_", "")
        with st.expander(f"Tree for Dynasty: {dynasty_id}", expanded=False):
            try:
                with open(image_path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode()
                
                # ADJUSTED HTML:
                # max-width is now 60%
                # hover scale reduced to 1.1
                image_html = f"""
                    <div style="overflow-x:auto; text-align: center;">
                        <img src="data:image/png;base64,{image_base64}" 
                             style="max-width: 60%; height: auto; margin: auto; display: block; transition: transform 0.2s; cursor: zoom-in;" 
                             onmouseover="this.style.transform='scale(1.1)'" 
                             onmouseout="this.style.transform='scale(1)'"/>
                    </div>
                """
                st.markdown(image_html, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Could not load image for {dynasty_id}: {e}")

############################
# Main Application
############################
        
def main():
    st.set_page_config(layout="wide")

    # Load configs into session state once
    if "configs_loaded" not in st.session_state:
        try:
            st.session_state.init_config = load_config("config/initialization.json")
            st.session_state.life_config = load_config("config/life_stages.json")
            st.session_state.configs_loaded = True
        except Exception as e:
            st.error(f"FATAL: Could not load configuration files. {e}")
            logging.exception("Failed to load initial configs")
            st.stop()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏛️ Dynasty Settings", 
        "🌳 Dynasty Trees", 
        "📜 Negative Events", 
        "💉 Life Cycle Modifiers"
    ])

    with tab1:
        display_dynasty_config(st.session_state.init_config)

    with tab2:
        display_generated_images("Dynasty Preview/")

    with tab3:
        # Pass the *same* config dict to the event editor
        display_event_config(st.session_state.init_config)
    
    with tab4:
        display_life_stage_config(st.session_state.life_config)

if __name__ == "__main__":
    main()