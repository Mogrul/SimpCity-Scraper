import logging
from pathlib import Path

from src.shared import Config
from .images import ImageDuplication
from .videos import VideoDuplication

class Duplication():
    def __init__(self):
        self._logger = logging.getLogger("duplication")
        self._config = Config()
    
    def check_duplicates(self, path: Path):
        if not path.exists():
            self._logger.error(f"Path doesn't exist: {path}")
            return
        
        if self._config.duplication.images:
            image_duplication = ImageDuplication(path)
            image_duplication.run()
        
        if self._config.duplication.videos:
            video_duplication = VideoDuplication(path)
            video_duplication.run()