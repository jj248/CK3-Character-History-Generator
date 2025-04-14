# CK3-Character-History-Generator
A Python-based tool designed to generate character history files for Crusader Kings III (CK3), facilitating the creation of custom characters, dynasties, and family trees for modding purposes.​
## Features
- **Character Generation:** Automates the creation of character entries with customizable attributes.
- **Dynasty Creation:** Supports the establishment of dynasties, linking characters through familial relationships.
- **Name Lists:** Utilizes configurable name lists to assign culturally appropriate names.
- **Configuration Files:** Allows for customization through external configuration files.
- **Family Trees:** Generates interconnected family structures, enhancing the depth of generated histories.
## Installation
1.  git clone https://github.com/jj248/CK3-Character-History-Generator.git
2.  cd CK3-Character-History-Generator
3.  pip install -r requirements.txt

*Note: Ensure you have Python 3.x installed on your system.*
## Usage
1.  **Configure Settings:**

Modify the configuration files located in the config/ directory to suit your modding needs.

2.  **Run the Generator:**

python main.py

This will execute the main script, generating character history files based on your configurations.

3.  **Review Output:**

The generated files will be available in the designated output directory, ready for integration into your CK3 mod.

## Project Structure
-   `main.py` – Entry point of the application.
-   `character.py` – Defines character attributes and behaviors.
-   `config_loader.py` – Handles loading and parsing of configuration files.
-   `name_loader.py` – Manages name list loading and assignment
-   `simulation.py` – Orchestrates the simulation of character histories.
-   `utils.py` – Contains utility functions used across the application.
-   `config/` – Directory containing configuration files.
-   `name_lists/` – Directory housing name list files.
  
## Contributing
Contributions are welcome! If you have suggestions for improvements or encounter issues, please open an issue or submit a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for details.