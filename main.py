import logging
import os
import sys
import statistics
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

# Toggle this to True if you want to collect & print stats of characters
STATS_ENABLED = True

# Toggle this to True if you want to print info about titles
TITLE_INFO_ENABLED = True


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
            marriage_year = progenitor_male.birth_year + life_stages_config.get('marriageMinAge', 18) + progenitor_male.numenorean_blood_tier*5 + random.randint(0, 4)
            print(marriage_year)
            simulation.marry_characters(progenitor_male, progenitor_female, marriage_year)
            # Ensure at least 3 children per dynasty
            for i in range(3):
                child_birth_year = marriage_year + random.randint(2, 4)  # Stagger births
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
            marriage_year = progenitor_male.birth_year + life_stages_config.get('marriageMinAge', 18) + progenitor_male.numenorean_blood_tier*5 + random.randint(0, 4)
            simulation.marry_characters(progenitor_male, progenitor_female, marriage_year)
            # Ensure at least 3 children per dynasty
            for i in range(3):
                child_birth_year = marriage_year  + random.randint(2, 4)  # Stagger births
                child = simulation.create_child(progenitor_female, progenitor_male, child_birth_year)
                if child:
                    simulation.add_character_to_pool(child)
                    simulation.all_characters.append(child)

    # Run the simulation
    simulation.run_simulation()

    # Gather Statistics
    if STATS_ENABLED:
        # 1) Gather a flat list of “records”
        records = []
        for c in simulation.all_characters:
            sex = c.sex
            gen = c.generation
            num_children = len(c.children)

            # age at death
            if c.death_year is not None:
                age_death = c.death_year - c.birth_year
            else:
                # never include survivors in the death‑age stats
                age_death = None

            # age at first marriage
            age_marriage = None
            # 1) try own events
            for date, ev in sorted(c.events):
                if ev.startswith("add_spouse") or ev.startswith("add_matrilineal_spouse"):
                    yr = int(date.split(".")[0])
                    age_marriage = yr - c.birth_year
                    break

            # 2) fallback: if has a spouse, scan their events for their ID
            if age_marriage is None and c.spouse:
                for date, ev in sorted(c.spouse.events):
                    if ev.endswith(c.char_id):
                        yr = int(date.split(".")[0])
                        age_marriage = yr - c.birth_year
                        break

            tier = c.numenorean_blood_tier or 0

            records.append({
                "sex": sex,
                "generation": gen,
                "children": num_children,
                "age_death": age_death,
                "age_marriage": age_marriage,
                "tier": tier
            })

        from collections import defaultdict
        import statistics

        # helper for avg children & marriages (unchanged)
        def summarize_mean(group_key, value_key):
            sums = defaultdict(int)
            counts = defaultdict(int)
            for r in records:
                k = r[group_key]
                v = r[value_key]
                if v is None:
                    continue
                sums[k] += v
                counts[k] += 1
            return {k: sums[k] / counts[k] for k in sums}

        sexes = ["Male", "Female"]
        total_count = len(records)

        # counts by sex
        count_by_sex = defaultdict(int)
        for r in records:
            count_by_sex[r["sex"]] += 1

        # avg kids
        sums, cnts = defaultdict(int), defaultdict(int)
        for r in records:
            sums[r["sex"]] += r["children"]
            cnts[r["sex"]] += 1
        avg_children = {s: (sums[s] / cnts[s] if cnts[s] else 0) for s in sexes}
        avg_children["Total"] = sum(sums.values()) / sum(cnts.values())

        # avg marriage
        avg_marriage = summarize_mean("sex", "age_marriage")
        total_marriages = [r["age_marriage"] for r in records if r["age_marriage"] is not None]
        avg_marriage["Total"] = (sum(total_marriages) / len(total_marriages)) if total_marriages else 0

        # ** new five‐number summary for age at death **
        death_stats = {}
        for s in sexes + ["Total"]:
            if s == "Total":
                ages = [r["age_death"] for r in records if r["age_death"] is not None]
            else:
                ages = [r["age_death"] for r in records if r["sex"] == s and r["age_death"] is not None]
            if ages:
                ages.sort()
                mn = ages[0]
                mx = ages[-1]
                # statistics.quantiles returns [Q1, Q2, Q3] for n=4
                q1, med, q3 = statistics.quantiles(ages, n=4, method="inclusive")
                death_stats[s] = {"min": mn, "p25": q1, "median": med, "p75": q3, "max": mx}
            else:
                death_stats[s] = {"min": None, "p25": None, "median": None, "p75": None, "max": None}

        # print
        print("\n--- Character Stats by Sex ---")
        print(f"{'Sex':<8} {'Count':>6} {'AvgKids':>8} {'AvgMarry':>10} {'DeathStats':>25}")
        for s in sexes + ["Total"]:
            stats = death_stats[s]
            if stats["min"] is None:
                ds = "—/—/—/—/—"
            else:
                ds = f"{stats['min']}/{stats['p25']}/{stats['median']}/{stats['p75']}/{stats['max']}"
            print(
                f"{s:<8} "
                f"{count_by_sex.get(s, total_count if s=='Total' else 0):>6} "
                f"{avg_children.get(s,0):8.2f} "
                f"{avg_marriage.get(s,0):10.2f} "
                f"{ds:>25}"
            )

        # b) tier breakdown per generation (unchanged)
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
            "Male":   statistics.mean(r["tier"] for r in records if r["sex"]=="Male"),
            "Female": statistics.mean(r["tier"] for r in records if r["sex"]=="Female")
        }
        print("Average Númenórean tier  |  Male:", round(avg_tier_by_sex["Male"],2),
            " Female:", round(avg_tier_by_sex["Female"],2))

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
    
    if TITLE_INFO_ENABLED:
        titles.print_title_histories()

    titles.write_title_histories_to_file()

    tree = FamilyTree("Character and Title files/family_history.txt", "Character and Title files/title_history.txt", config_loader.config)  # Ensure both files exist
    tree.build_trees()
    tree.render_trees()

if __name__ == "__main__":
    run_main()
