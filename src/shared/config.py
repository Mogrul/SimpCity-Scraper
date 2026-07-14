from pathlib import Path
import json
import logging

from .singleton_meta import SingletonMeta
from .args import get_args

class Config(metaclass = SingletonMeta):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._args = get_args()
        
    def exists(self, json_path = Path("config.json")) -> bool:
        return json_path.exists()
    
    def load(self, json_path = Path("config.json")):
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
        
        # Network configs
        network = data.get("network", {})
        
        self.headers = network.get("headers")
        self.workers = network.get("workers")
        self.timeout = network.get("timeout")
        self.chunk_size = network.get("chunk_size")
        self.cookie_path = Path(network.get("cookie_path"))
        
        # Scraper configs
        scraper = data.get("scraper", {})
                
        self.save_metadata = bool(scraper.get("save_metadata"))
        self.download_location = Path(scraper.get("download_location"))
        self.check_duplicates = bool(scraper.get("check_duplicates"))
        self.check_duplicate_threshold = float(scraper.get("check_duplicate_threshold"))
        self.urls = self._args.urls
        
        success = all(
            value is not None
            for value in vars(self).values()
        )
        
        if success:
            if not self.headers:
                return success
             
            header_str_list = [
                f"{key}: {value}"
                for key, value
                in self.headers.items()
            ]
            
            self._logger.info(
                "\n"
                "Program starting with configs:\n"
                "   Network:\n"
                f"      Headers:\n          {'\n          '.join(header_str_list)}\n"
                f"      Workers: {self.workers}\n"
                f"      Timeout: {self.timeout}\n"
                f"      Cookies Location: {self.cookie_path}\n\n"
                "   Scraper:\n"
                f"       Save Metdata: {self.save_metadata}\n"
                f"       Download Location: {self.download_location}\n"
                f"       URLs: {self.urls}"
                "\n"
            )
        
        return success
    
    def generate(self, destination = Path("config.json")):
        data = {
            "network": {
                "headers": {},
                "workers": 10,
                "timeout": 10,
                "chunk_size": 1048576,
                "cookie_path": ".cookies"
            },
            "scraper": {
                "save_metadata": 0,
                "download_location": "Downloads"
            }
        }
        
        with open(destination, "w") as f:
            json.dump(data, f, indent = 4)