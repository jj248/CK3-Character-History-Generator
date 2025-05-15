import json
import os
import logging

###############################
### Imported to other files ###
###############################
# Toggle this to True if you want to print debug statements scattered throughout the code
# WARNING: There are a LOT of print statements
DEBUG_PRINT = False

# Toggle this to True if you want to collect & print stats of characters
STATS_ENABLED = True

# Toggle this to True if you want to collect & print stats of numenorean blood and its inheritance
NUMENOREAN_BLOOD_STATS = False

# Toggle this to True if you want to print info about titles
TITLE_INFO_ENABLED = False

# Toggle this to True if you want to print info about which files were loaded and to where they were exported
LOADED_INFO_FILES = False

# Toggle this to run several simulations. 
# NB: Does not save each iteration, this is simply used to get an X amount of statistics in one go
NUM_SIMULATIONS = 1
###############################

class ConfigLoader:
    def __init__(self, config_folder='config'):
        self.config_folder = config_folder
        self.config = {}
        self.load_configs()
        self.validate_configs()
        self.build_language_rules()

    def load_configs(self):
        config_files = {
            'initialization': 'initialization.json',
            'skills_and_traits': 'skills_and_traits.json',
            'life_stages': 'life_stages.json'
        }

        for category, filename in config_files.items():
            file_path = os.path.join(self.config_folder, filename)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Configuration file {filename} not found in {self.config_folder}.")
            with open(file_path, 'r', encoding='utf-8') as file:
                try:
                    self.config[category] = json.load(file)
                    if LOADED_INFO_FILES:
                        logging.info(f"Loaded configuration from {filename}.")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Error parsing {filename}: {e}")

    def validate_configs(self):
        # Validate initialization config
        initialization = self.config.get('initialization', {})
        required_initialization = ['dynasties', 'initialCharID', 'minYear', 'maxYear', 'generationMax']
        for key in required_initialization:
            if key not in initialization:
                raise ValueError(f"Missing '{key}' in initialization configuration.")

        # Validate dynasties
        dynasties = self.config.get('initialization', {}).get('dynasties', [])
        if not dynasties:
            raise ValueError("No dynasties defined in initialization configuration.")

        for dynasty in dynasties:
            required_dynasty_fields = ['dynastyID', 'faithID', 'cultureID', 'gender_law', 'succession', 'progenitorMaleBirthYear', 'nameInheritance']
            for field in required_dynasty_fields:
                if field not in dynasty:
                    raise ValueError(f"Missing '{field}' in dynasty configuration.")

            # Validate nameInheritance fields
            name_inheritance = dynasty['nameInheritance']
            required_inheritance_fields = ['grandparentNameInheritanceChance', 'parentNameInheritanceChance', 'noNameInheritanceChance']
            for field in required_inheritance_fields:
                if field not in name_inheritance:
                    raise ValueError(f"Missing '{field}' in nameInheritance configuration for dynasty {dynasty['dynastyID']}.")

            # Check if chances sum to 1
            total_chance = sum(name_inheritance.values())
            if not abs(total_chance - 1.0) < 1e-6:
                raise ValueError(f"Name inheritance chances for dynasty {dynasty['dynastyID']} do not sum to 1.")
				
        # Validate bastardy chances
        life_stages = self.config.get('life_stages', {})
        if 'bastardyChanceMale' not in life_stages or 'bastardyChanceFemale' not in life_stages:
            raise ValueError("Missing bastardyChanceMale or bastardyChanceFemale in life_stages configuration.")

        bastardy_chances = {
            'bastardyChanceMale': life_stages['bastardyChanceMale'],
            'bastardyChanceFemale': life_stages['bastardyChanceFemale']
        }
        for key, value in bastardy_chances.items():
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{key} must be between 0 and 1.")				
		
		# Validate mortalityRates
        life_stages = self.config.get('life_stages', {})
        mortality_rates = life_stages.get('mortalityRates', {})
        for sex in ['Male', 'Female']:
            if sex not in mortality_rates:
                raise ValueError(f"Mortality rates for {sex} are not defined in life_stages configuration.")
            if len(mortality_rates[sex]) != 121:
                raise ValueError(
                    f"Mortality rates for {sex} must have exactly 121 entries (ages 0 to 120). "
                    f"Current count: {len(mortality_rates[sex])}"
                )

        # Validate marriageRates
        marriage_rates = life_stages.get('marriageRates', {})
        for sex in ['Male', 'Female']:
            if sex not in marriage_rates:
                raise ValueError(f"Marriage rates for {sex} are not defined in life_stages configuration.")
            if len(marriage_rates[sex]) != 121:
                raise ValueError(
                    f"Marriage rates for {sex} must have exactly 121 entries (ages 0 to 120). "
                    f"Current count: {len(marriage_rates[sex])}"
                )

        # Validate fertilityRates
        fertility_rates = life_stages.get('fertilityRates', {})
        for sex in ['Male', 'Female']:
            if sex not in fertility_rates:
                raise ValueError(f"Fertility rates for {sex} are not defined in life_stages configuration.")
            if len(fertility_rates[sex]) != 121:
                raise ValueError(
                    f"Fertility rates for {sex} must have exactly 121 entries (ages 0 to 120). "
                    f"Current count: {len(fertility_rates[sex])}"
                )

        # Validate maximumNumberOfChildren
        if 'maximumNumberOfChildren' not in life_stages:
            raise ValueError("Missing 'maximumNumberOfChildren' in life_stages configuration.")
        if not isinstance(life_stages['maximumNumberOfChildren'], int) or life_stages['maximumNumberOfChildren'] < 0:
            raise ValueError("'maximumNumberOfChildren' must be a non-negative integer.")

        # Validate minimumYearsBetweenChildren
        if 'minimumYearsBetweenChildren' not in life_stages:
            raise ValueError("Missing 'minimumYearsBetweenChildren' in life_stages configuration.")
        if not isinstance(life_stages['minimumYearsBetweenChildren'], int) or life_stages['minimumYearsBetweenChildren'] < 0:
            raise ValueError("'minimumYearsBetweenChildren' must be a non-negative integer.")

        # Validate childbirthMinAge and childbirthMaxAge are removed
        if 'childbirthMinAge' in life_stages or 'childbirthMaxAge' in life_stages:
            logging.warning("Parameters 'childbirthMinAge' and 'childbirthMaxAge' are obsolete and have been removed. Please update your configuration accordingly.")

        # Validate skills_and_traits config
        skills_and_traits = self.config.get('skills_and_traits', {})
        required_skills_and_traits = ['sexualityDistribution', 'skillProbabilities', 'educationProbabilities', 'personalityTraits']
        for key in required_skills_and_traits:
            if key not in skills_and_traits:
                raise ValueError(f"Missing '{key}' in skills_and_traits configuration.")
				
		# Validate educationWeightExponent
        skills_and_traits = self.config.get('skills_and_traits', {})
        education_weight_exponent = skills_and_traits.get('educationWeightExponent', 1)
        if not isinstance(education_weight_exponent, (int, float)) or education_weight_exponent < 1:
            logging.warning("Invalid 'educationWeightExponent' in skills_and_traits configuration. Using default value of 1.")
            self.config['skills_and_traits']['educationWeightExponent'] = 1

        # Flag unused parameters
        # Initialization Configuration Unused Parameters
        initialization_unused = ['bookmarkStartDate', 'childrenMax']
        for key in initialization_unused:
            if key in initialization:
                logging.warning(f"Initialization parameter '{key}' is currently unused.")

        # Skills and Traits Configuration Unused Parameters
        skills_and_traits_unused = ['inheritanceChance', 'downgradeChance', 'randomMutationChance', 'mutationProbabilities']
        for key in skills_and_traits_unused:
            if key in skills_and_traits:
                logging.warning(f"Skills and Traits parameter '{key}' is currently unused.")

        # Life Stages Configuration Unused Parameters
        life_stages_unused = ['battleDeathChance', 'illDeathChance', 'intrigueDeathChance', 
                              'oldDeathMinAge', 'oldDeathMaxAge', 'siblingMinSpacing']
        for key in life_stages_unused:
            if key in life_stages:
                logging.warning(f"Life Stages parameter '{key}' is currently unused.")

    def get_initialization_config(self):
        return self.config.get('initialization', {})
		
    def get_dynasty_config(self, dynasty_id):
        dynasties = self.config.get('initialization', {}).get('dynasties', [])
        for dynasty in dynasties:
            if dynasty['dynastyID'] == dynasty_id:
                return dynasty
        return None

    def get_skills_and_traits_config(self):
        return self.config.get('skills_and_traits', {})

    def get_life_stages_config(self):
        return self.config.get('life_stages', {})

    def get(self, category, key, default=None):
        return self.config.get(category, {}).get(key, default)
    
    # ------------------------------------------------------------
    #  Languages: dynasty_id → list[(language_id, start_year, end_year)]
    # ------------------------------------------------------------
    def build_language_rules(self) -> None:
        """Parse the optional 'languages' array for every dynasty."""
        self.dynasty_language_rules: dict[str, list[tuple[str,int,int]]] = {}

        dynasties = self.config.get('initialization', {}).get('dynasties', [])
        for entry in dynasties:
            lang_rules = []
            for spec in entry.get('languages', []):
                try:
                    lang, start, end = spec.split(',')
                    lang_rules.append((lang.strip(), int(start), int(end)))
                except ValueError:
                    logging.warning(
                        f"Bad language spec '{spec}' in dynasty {entry.get('dynastyID')}"
                    )
            self.dynasty_language_rules[entry['dynastyID']] = lang_rules

    def get_language_rules(self):
        return self.dynasty_language_rules

