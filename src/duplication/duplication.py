import logging
from pathlib import Path
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image
import imagehash

from src.shared import Config
from .images import ImageDuplication

class Duplication():
    def __init__(self):
        self._logger = logging.getLogger("duplication")
        self._config = Config()
        
        self._image_hashes: dict[Path, imagehash.ImageHash] = {}
        self._image_deleted: set[Path] = set()
        self._image_deleted_lock = Lock()
    
    def check_duplicates(self, path: Path):
        if not path.exists():
            self._logger.error(f"Path doesn't exist: {path}")
            return
        
        image_duplication = ImageDuplication(path)
        image_duplication.run()
        