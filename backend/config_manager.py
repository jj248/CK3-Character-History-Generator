import json
import os
from typing import Dict, Any

class ConfigManager:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)

    def _load_json(self, filename: str) -> Dict[str, Any]:
        filepath = os.path.join(self.config_dir, filename)
        if not os.path.exists(filepath):
            return {}
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_json(self, filename: str, data: Dict[str, Any]) -> None:
        filepath = os.path.join(self.config_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get_life_stages(self) -> Dict[str, Any]:
        return self._load_json("life_stages.json")

    def get_initialization(self) -> Dict[str, Any]:
        return self._load_json("initialization.json")

    def get_traits(self) -> Dict[str, Any]:
        return self._load_json("traits.json")
