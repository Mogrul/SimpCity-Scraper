from pathlib import Path
import json
import logging

from src.shared.singleton_meta import SingletonMeta

class Config(metaclass = SingletonMeta):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        
        # Network configs
        self.headers: dict | None = None
        self.workers: int | None = None
        self.timeout: int | None = None
        
    def exists(self, json_path = Path("config.json")) -> bool:
        return json_path.exists()
    
    def load_json(self, json_path = Path("config.json")):
        if not json_path.exists():
            return False
        
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
        
        except Exception as e:
            self._logger.critical(f"Failed to load {json_path}: {e}")
            return False
        
        if not isinstance(data, dict):
            return False
        
        network = data.get("network", {})
        
        self.headers = network.get("headers")
        self.workers = network.get("workers")
        self.timeout = network.get("timeout")
        
        return all(
            value is not None
            for value in vars(self).values()
        )
    
    def generate(self, destination = Path("config.json")):
        data = {
            "network": {
                "headers": {},
                "workers": 10,
                "timeout": 10
            }
        }
        
        with open(destination, "w") as f:
            json.dump(data, f, indent = 4)