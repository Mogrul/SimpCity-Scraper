from pathlib import Path
import tomllib
import os

from .models import (
    Network, Scraper, Duplication
)
from .models import Config as ConfigData
from .singleton_meta import SingletonMeta
from .args import get_args

class Config(metaclass = SingletonMeta):
    def __init__(self):
        pass
    
    def load_config(self):
        # Load from TOML file
        with open("config.toml", "rb") as f:
            data = tomllib.load(f)
            
        config = ConfigData(
            duplication = Duplication(
                videos = data["duplication"]["videos"],
                images = data["duplication"]["images"],
                samples = data["duplication"]["samples"],
                threshold = data["duplication"]["threshold"]
            ),
            scraper = Scraper(
                download_location = Path(data["scraper"]["download_location"]),
                extractor_location = Path(data["scraper"]["extractor_location"]),
                extract_files = data["scraper"]["extract_files"],
                skip_scrapers = data["scraper"]["skip_scrapers"]
            ),
            network = Network(
                workers = data["network"]["workers"],
                timeout = data["network"]["timeout"],
                chunk_size = data["network"]["chunk_size"],
                cookie_path = Path(data["network"]["cookie_path"]),
                headers = data["network"]["headers"]
            )
        )
        
        self.duplication = config.duplication
        self.scraper = config.scraper
        self.network = config.network
        
        # Load configs from args
        args = get_args()
        self.urls: list[str] = args.urls
        
        if args.config:
            self._display_config()
            os.abort()
    
    def _display_config(self):
        header_str = (
            "               " + "\n               ".join(
                [
                    f"{f'{key}:':<20} {value}"
                    for key, value
                    in self.network.headers.items()
                ]
            )
        )
        
        print(
            f"SimpCity Scraper Configs:\n",
            "     Duplication:\n"
            f"           {'Videos:':<25}{self.duplication.videos}\n"
            f"           {'Images:':<25}{self.duplication.images}\n"
            f"           {'Samples:':<25}{self.duplication.samples}\n"
            f"           {'Threshold:':<25}{self.duplication.threshold}\n"
            "\n"
            "      Scraper:\n"
            f"           {'Download Location:':<25}{self.scraper.download_location}\n"
            f"           {'Extractor Location:':<25}{self.scraper.extract_files}\n"
            f"           {'Extract Files:':<25}{self.scraper.extract_files}\n"
            f"           {'Skip Scrapers:':<25}{self.scraper.skip_scrapers}\n"
            "\n"
            "      Network:\n"
            f"           {'Workers:':<25}{self.network.workers}\n"
            f"           {'Timeout:':<25}{self.network.timeout}\n"
            f"           {'Chunk Size:':<25}{self.network.chunk_size}\n"
            f"           {'Cookie Path:':<25}{self.network.cookie_path}\n"
            f"           {'Headers:':<25}\n"
            + header_str
        )