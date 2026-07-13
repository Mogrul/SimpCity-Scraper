from argparse import Namespace
from pathlib import Path
import logging

import yaml

from src.util import resource_path, format_bytes

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
        self.remove_image_duplicates = True
        self.remove_video_duplicates = True
        self.similarity_threshold = 0.9
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
            config_path = "config.yaml"
    ) -> bool:
        """Loads the configs from args and the config.yaml path

        Args:
            args (Namespace): Namespace retrieved from the parsing of arguments.
            config_path (str, optional): Path to the config.yaml file. Defaults to "config.yaml".

        Returns:
            bool: True if success, False if not.
        """
        urls = args.urls
        
        with open(resource_path(config_path), "r") as f:
            data = yaml.safe_load(f)
        
        if not isinstance(data, dict):
            self._logger.critical(f"Failed to extract settings from {config_path}")
            
            return False
        
        downloads = data.get("downloads", {})
        
        output = downloads.get("output")
        remove_image_duplicates = downloads.get("remove_image_duplicates")
        remove_video_duplicates = downloads.get("remove_video_duplicates")
        similarity_threshold = downloads.get("similarity_threshold")
        chunk_size = downloads.get("chunk_size")
        
        network = data.get("network", {})
        
        timeout = network.get("timeout")
        user_agent = network.get("user_agent")
        workers = network.get("workers")
        
        filters = data.get("filters", {})
        
        excluded_domains = filters.get("excluded_domains")
        
        if isinstance(output, str):
            output = Path(output)
        
        self.urls = urls
        
        self.output = output
        self.remove_image_duplicates = remove_image_duplicates
        self.remove_video_duplicates = remove_video_duplicates
        self.similarity_threshold = similarity_threshold
        
        self.timeout = timeout
        self.user_agent = user_agent
        self.workers = workers
        self.chunk_size = chunk_size
        
        self.excluded_domains = excluded_domains
        
        return True
    
    def verify_config(self) -> bool:
        """Verifies that all the values in the config are the object types they should be.

        Returns:
            bool: True if passed, False if not.
        """
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
            self.remove_video_duplicates,
            self.remove_image_duplicates
        ])
        
        if not bool_verify:
            self._logger.critical(f"One or more bools are invalid!")
            return False
        
        # float verify
        float_verify = self._verify_by_class(float, [
            self.similarity_threshold
        ])
        
        if not float_verify:
            self._logger.critical(f"One or more floats are invalid!")
            return False
        
        self._logger.info(
            "Initialised with configs:\n"
            "   Downloads:\n"
            f"      Remove Image Duplicates: {self.remove_image_duplicates}\n"
            f"      Remove Video Duplicates: {self.remove_video_duplicates}\n"
            f"      Similarity Threshold: {self.similarity_threshold * 100}%\n"
            f"      Chunk Size: {format_bytes(self.chunk_size)}\n"
            "\n"
            "   Network:\n"
            f"      Timeout: {self.timeout} seconds\n"
            f"      User Agent: {self.user_agent}\n"
            f"      Workers: {self.workers}\n"
            "\n"
            "   Filters:\n"
            f"      Excluded Domains: {self.excluded_domains}"
        )
        
        return True
        
    def _verify_by_class(self, cls: type, objects: list[object]) -> bool:
        """Verify config helper function to verify a list of objects are the object type they should be.

        Args:
            cls (type): Object type to check against the objects.
            objects (list[object]): List of objects to check the type again.

        Returns:
            bool: True of passed, False if not.
        """
        if not all(isinstance(x, cls) for x in objects):
            return False
        
        return True
        