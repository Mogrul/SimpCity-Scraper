from argparse import Namespace
from pathlib import Path

import yaml
import logging

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        
        return cls._instance
    
    def __init__(self):
        if getattr(self, "_initialised", False):
            return
        
        self._initialised = True
        
        self._logger = logging.getLogger("config")
        
        self.urls: list[str] = [] # Passed in args
        
        # Download settings
        self.output = Path("Downloads")
        self.remove_duplicates = True
        self.chunk_size = 1_048_576
        
        # Network settings
        self.timeout = 30
        self.user_agent = {}
        self.workers = 10
        
        # Filtering options
        self.excluded_domains: list[str] = []
    
    def load_config(
            self,
            args: Namespace,
            config_path = Path("config.yaml")
    ) -> bool:
        urls = args.urls
        
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
        
        if not isinstance(data, dict):
            self._logger.critical(f"Failed to extract settings from {config_path}")
            
            return False
        
        downloads = data.get("downloads", {})
        
        output = downloads.get("output", Path("Downloads"))
        remove_duplicates = downloads.get("remove_duplicates", True)
        chunk_size = downloads.get("chunk_size", 1_048_576)
        
        network = data.get("network", {})
        
        timeout = network.get("timeout", 30)
        user_agent = network.get("user_agent", {})
        workers = network.get("workers", 10)
        
        filters = data.get("filters", {})
        
        excluded_domains = filters.get("excluded_domains", [])
        
        if isinstance(output, str):
            output = Path(output)
        
        if isinstance(remove_duplicates, str):
            remove_duplicates = bool(remove_duplicates)
        
        self.urls = urls
        
        self.output = output
        self.remove_duplicates = remove_duplicates
        
        self.timeout = timeout
        self.user_agent = user_agent
        self.workers = workers
        self.chunk_size = chunk_size
        
        self.excluded_domains = excluded_domains
        
        return True
    
    def verify_config(self) -> bool:
        # Int verify
        int_success = self._verify_by_class(int, [
            self.chunk_size,
            self.timeout,
            self.workers
        ])
        
        if not int_success:
            self._logger.critical(f"One or more ints are invalid!")
            return False
        
        # Path verify
        path_success = self._verify_by_class(Path, [
            self.output
        ])
        
        if not path_success:
            self._logger.critical(f"One or more paths are invalid!")
            return False
        
        # list verify
        list_success = self._verify_by_class(list, [
            self.excluded_domains
        ])
        
        if not list_success:
            self._logger.critical(f"One or more lists are invalid!")
            return False
        
        # dict verify
        dict_verify = self._verify_by_class(dict, [
            self.user_agent
        ])
        
        if not dict_verify:
            self._logger.critical(f"One or more dictionaries are invalid!")
            return False
        
        # bool verify
        bool_verify = self._verify_by_class(bool, [
            self.remove_duplicates
        ])
        
        if not bool_verify:
            self._logger.critical(f"One or more bools are invalid!")
            return False
        
        return True
        
    def _verify_by_class(self, cls: type, objects: list[object]) -> bool:
        if not all(isinstance(x, cls) for x in objects):
            return False
        
        return True
        