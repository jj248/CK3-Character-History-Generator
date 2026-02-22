import logging
import os
import sys
import statistics
import random
from collections import defaultdict
from ck3gen.config_loader import (
    STATS_ENABLED, NUMENOREAN_BLOOD_STATS, TITLE_INFO_ENABLED,
    NUM_SIMULATIONS, GENERATE_IMAGE_BOOL, ConfigLoader
)
from ck3gen.family_tree import FamilyTree
from ck3gen.name_loader import NameLoader
from ck3gen.simulation import Simulation
from ck3gen.character import Character
from ck3gen.title_history import CharacterLoader  # Needed for original logic
from ck3gen.title_history import TitleHistory      # Needed for original logic
from ck3gen.dynasty_creation import (
    generate_dynasty_definitions, generate_dynasty_name_localization,
    generate_dynasty_motto_localization
)
from utils.utils import generate_char_id

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
        handlers=[logging.StreamHandler()]
    )

def generate_game_files(config_loader):
    """Generates dynasty definition and localization files from config."""
    logging.info("Generating dynasty game files...")
    try:
        dynasty_config_path = get_resource_path("config/initialization.json")
        generate_dynasty_definitions(dynasty_config_path, "dynasty_definitions.txt")
        generate_dynasty_name_localization(dynasty_config_path, "lotr_dynasty_names_l_english.yml")
        generate_dynasty_motto_localization(dynasty_config_path, "lotr_mottos_l_english.yml")
    except Exception as e:
        logging.error(f"Failed to generate game files: {e}")
        raise

def create_progenitor_couple(dynasty_config, simulation, config_loader, name_loader):
    """Creates and marries a progenitor couple for a given dynasty."""
    
    # --- 1. Load Config Values ---
    skills_config = config_loader.get_skills_and_traits_config()
    life_stages_config = config_loader.get_life_stages_config()
    
    dynasty_id = dynasty_config['dynastyID']
    culture_id = dynasty_config['cultureID']
    religion_id = dynasty_config['faithID']
    gender_law = dynasty_config['gender_law']
    is_house = dynasty_config['isHouse']
    progenitor_birth_year = dynasty_config['progenitorMaleBirthYear']
    tier = dynasty_config.get('numenorBloodTier', 0)
    dynasty_prefix = dynasty_id.split('_')[1] if '_' in dynasty_id else dynasty_id

    # --- 2. Determine Genders ---
    if gender_law in ["ENATIC", "ENATIC_COGNATIC"]:
        primary_sex = "Female"
        spouse_sex = "Male"
    else:
        primary_sex = "Male"
        spouse_sex = "Female"

    # --- 3. Create Primary (Noble) Character ---
    progenitor_char_id = generate_char_id(dynasty_prefix, simulation.dynasty_char_counters)
    progenitor_name = name_loader.load_names(culture_id, primary_sex.lower())
    progenitor = Character(
        char_id=progenitor_char_id,
        name=progenitor_name,
        sex=primary_sex,
        birth_year=progenitor_birth_year,
        dynasty=dynasty_id,
        is_house=is_house,
        culture=culture_id,
        religion=religion_id,
        gender_law=gender_law,
        sexuality_distribution=skills_config['sexualityDistribution'],
        generation=1,
        is_progenitor=True,
        birth_order=1
    )
    progenitor.age = 18  # Set initial age
    progenitor.numenorean_blood_tier = tier
    simulation.add_character_to_pool(progenitor)
    simulation.all_characters.append(progenitor)

    # --- 4. Create Spouse (Lowborn) ---
    spouse_char_id = generate_char_id(dynasty_prefix, simulation.dynasty_char_counters)
    spouse_name = name_loader.load_names(culture_id, spouse_sex.lower())
    spouse = Character(
        char_id=spouse_char_id,
        name=spouse_name,
        sex=spouse_sex,
        birth_year=progenitor_birth_year,  # Same year
        dynasty=None,  # Lowborn
        is_house=is_house,
        culture=culture_id,
        religion=religion_id,
        gender_law=gender_law,
        sexuality_distribution=skills_config['sexualityDistribution'],
        generation=1,
        is_progenitor=True, # Also progenitor to ensure they live
        birth_order=1
    )
    spouse.numenorean_blood_tier = tier
    simulation.add_character_to_pool(spouse)
    simulation.all_characters.append(spouse)

    # --- 5. Marry Them & Create Children ---
    marriage_year = progenitor.birth_year + life_stages_config.get('marriageMinAge', 18) + (progenitor.numenorean_blood_tier or 0) * 5 + random.randint(0, 4)
    
    # Assign correct pointers for marriage and child creation
    male, female = (progenitor, spouse) if progenitor.sex == "Male" else (spouse, progenitor)
    
    simulation.marry_characters(male, female, marriage_year)
    
    # Ensure at least 3 children per dynasty
    for _ in range(3):
        child_birth_year = marriage_year + random.randint(2, 4)  # Stagger births
        child = simulation.create_child(female, male, child_birth_year)
        if child:
            simulation.add_character_to_pool(child)
            simulation.all_characters.append(child)

def setup_simulation(config_loader, name_loader):
    """Initializes the Simulation object and creates all progenitors."""
    logging.info("Setting up simulation and progenitors...")
    simulation = Simulation(config_loader.config, name_loader)
    initialization_config = config_loader.get_initialization_config()

    for dynasty_config in initialization_config.get('dynasties', []):
        create_progenitor_couple(dynasty_config, simulation, config_loader, name_loader)
        
    return simulation

def _gather_stats(simulation):
    """Helper to process all characters and return a list of stat records."""
    records = []
    lowborn_married_count = 0
    total_num_char = 0
    
    for c in simulation.all_characters:
        total_num_char += 1
        
        if c.dynasty and c.spouse and c.spouse.dynasty == "Lowborn" and c.dynasty != "Lowborn":
            lowborn_married_count += 1
            
        # Age at death
        age_death = c.death_year - c.birth_year if c.death_year is not None else None

        # Age at first marriage — read the attribute set directly in marry_characters
        age_marriage = (c.marriage_year - c.birth_year) if c.marriage_year is not None else None

        records.append({
            "sex": c.sex,
            "generation": c.generation,
            "children": len(c.children),
            "age_death": age_death,
            "age_marriage": age_marriage,
            "tier": c.numenorean_blood_tier or 0,
        })
        
    percent_lowborn_marriage = (lowborn_married_count / total_num_char) * 100 if total_num_char > 0 else 0
    
    return records, lowborn_married_count, total_num_char, percent_lowborn_marriage

def _print_stats(records, percentages_array):
    """Helper to print all formatted statistics to the console."""
    
    # --- Helper for avg children & marriages ---
    def summarize_mean(group_key, value_key):
        sums = defaultdict(int)
        counts = defaultdict(int)
        for r in records:
            k = r[group_key]
            v = r[value_key]
            if v is None: continue
            sums[k] += v
            counts[k] += 1
        return {k: sums[k] / counts[k] for k in sums}

    sexes = ["Male", "Female"]
    total_count = len(records)

    count_by_sex = defaultdict(int)
    for r in records:
        count_by_sex[r["sex"]] += 1

    # Avg kids
    sums, cnts = defaultdict(int), defaultdict(int)
    for r in records:
        sums[r["sex"]] += r["children"]
        cnts[r["sex"]] += 1
    avg_children = {s: (sums[s] / cnts[s] if cnts[s] else 0) for s in sexes}
    avg_children["Total"] = sum(sums.values()) / (sum(cnts.values()) or 1)

    # Avg marriage
    avg_marriage = summarize_mean("sex", "age_marriage")
    total_marriages = [r["age_marriage"] for r in records if r["age_marriage"] is not None]
    avg_marriage["Total"] = (sum(total_marriages) / len(total_marriages)) if total_marriages else 0

    # Five-number summary for age at death
    death_stats = {}
    for s in sexes + ["Total"]:
        key = s if s == "Total" else "sex"
        ages = [r["age_death"] for r in records if r["age_death"] is not None and (s == "Total" or r["sex"] == s)]
        
        if ages:
            ages.sort()
            mn, mx = ages[0], ages[-1]
            q1, med, q3 = statistics.quantiles(ages, n=4, method="inclusive")
            death_stats[s] = {"min": mn, "p25": q1, "median": med, "p75": q3, "max": mx}
        else:
            death_stats[s] = {"min": None, "p25": None, "median": None, "p75": None, "max": None}

    # Print main stats table
    print("\n--- Character Stats by Sex ---")
    print(f"{'Sex':<8} {'Count':>6} {'AvgKids':>8} {'AvgMarry':>10} {'DeathStats (min/25/med/75/max)':>30}")
    for s in sexes + ["Total"]:
        stats = death_stats[s]
        ds = "—/—/—/—/—" if stats["min"] is None else f"{stats['min']}/{stats['p25']}/{stats['median']}/{stats['p75']}/{stats['max']}"
        
        count = count_by_sex.get(s, total_count if s == 'Total' else 0)
        
        print(
            f"{s:<8} "
            f"{count:>6} "
            f"{avg_children.get(s, 0):8.2f} "
            f"{avg_marriage.get(s, 0):10.2f} "
            f"{ds:>30}"
        )

    # Print Numenorean stats
    if NUMENOREAN_BLOOD_STATS:
        gen_tier_counts = defaultdict(lambda: defaultdict(int))
        gen_totals = defaultdict(int)
        for r in records:
            g, t = r["generation"], r["tier"]
            gen_tier_counts[g][t] += 1
            gen_totals[g] += 1
            
        print("\n--- Numenor Tier Counts & % by Generation ---")
        for g in sorted(gen_totals):
            line_counts = gen_tier_counts[g]
            print(f"Gen {g}: total={gen_totals[g]}", end="")
            for t in sorted(line_counts):
                cnt = line_counts[t]
                pct = cnt / gen_totals[g] * 100
                print(f"  Tier{t}={cnt}({pct:.1f}%)", end="")
            print()

        avg_tier_by_sex = {
            "Male": statistics.mean(r["tier"] for r in records if r["sex"] == "Male"),
            "Female": statistics.mean(r["tier"] for r in records if r["sex"] == "Female")
        }
        print("Average Númenórean tier  |  Male:", round(avg_tier_by_sex["Male"], 2),
              " Female:", round(avg_tier_by_sex["Female"], 2))

    # Print average lowborn marriage %
    if percentages_array:
        average_lowborn_marriage_percent = sum(percentages_array) / len(percentages_array)
        print("\n===============================")
        print(f"Average % of Lowborn Marriages across {NUM_SIMULATIONS} runs: {average_lowborn_marriage_percent:.2f}%")
        print("===============================")

def run_and_analyze_simulations(config_loader, name_loader):
    """Runs the simulation N times, rebuilding state each run, and returns the final simulation."""
    percentages_array = []
    simulation = None

    for i in range(NUM_SIMULATIONS):
        print("-------------------------------")
        print(f"--- Running Simulation {i + 1}/{NUM_SIMULATIONS} ---")
        print("-------------------------------")

        # Rebuild from scratch each run so state does not accumulate across iterations
        simulation = setup_simulation(config_loader, name_loader)
        simulation.run_simulation()

        if STATS_ENABLED:
            records, lowborn_count, total_char, percent_lowborn = _gather_stats(simulation)
            percentages_array.append(percent_lowborn)

            print(f"\nTotal lowborns married into noble dynasties: {lowborn_count}")
            print(f"Percentage of Lowborn Marriages: {percent_lowborn:.2f}%")

            _print_stats(records, percentages_array)

    return simulation


def generate_output_files(simulation, config_loader):
    """
    Exports all data using the original, file-based loading
    logic to ensure compatibility with unchanged classes.
    """
    logging.info("Generating output files...")
    
    # 1. Export the character history text file
    simulation.export_characters("family_history.txt")

    # 2. Build Title History (Original file-based logic)
    character_loader = CharacterLoader()
    character_loader.load_characters("Character and Title files/family_history.txt")
    
    dynasty_config_path = get_resource_path("config/initialization.json")
    titles = TitleHistory(character_loader, dynasty_config_path)
    titles.build_title_histories()
    
    if TITLE_INFO_ENABLED:
        titles.print_title_histories()
    titles.write_title_histories_to_file()

    # 3. Build Family Tree Images (Original file-based logic)
    if GENERATE_IMAGE_BOOL:
        logging.info("Generating family tree images...")
        tree = FamilyTree(
            "Character and Title files/family_history.txt",
            "Character and Title files/title_history.txt",
            config_loader.config
        )
        tree.build_trees()
        tree.render_trees()

def run_main():
    """Main execution function."""
    
    # 1. Initial Setup
    setup_logging()
    try:
        config_loader = ConfigLoader('config')
        Character.DYNASTY_LANGUAGE_RULES = config_loader.get_language_rules()
        name_loader = NameLoader('name_lists')
    except Exception as e:
        logging.error(f"Failed to load configuration or name lists: {e}")
        return

    # 2. Generate Game Files
    generate_game_files(config_loader)

    # 3. Setup is now handled inside run_and_analyze_simulations per run

    # 4. Run Simulation(s) and Analyze — returns the final simulation for output
    simulation = run_and_analyze_simulations(config_loader, name_loader)

    if simulation is None:
        logging.error("No simulation was completed. Skipping output generation.")
        return

    # 5. Generate Final Output Files
    generate_output_files(simulation, config_loader)

    logging.info("--- Simulation Complete ---")


if __name__ == "__main__":
    run_main()