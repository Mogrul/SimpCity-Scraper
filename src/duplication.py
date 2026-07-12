import threading
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor

from PIL import Image
import imagehash
from imagehash import ImageHash

from .util import is_image, format_bytes

class Duplication:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        
        return cls._instance
    
    def __init__(self):
        if getattr(self, "_initialised", False):
            return
        
        self.hashes: dict[Path, ImageHash] = {}
        self.deleted = set()
        self.logger = logging.getLogger("duplication")
        self.lock = threading.Lock()
        
        self._initialised = True

    def check_duplicate_images(
            self,
            path: Path,
            recursive = True,
            similarity_threshold = 0.90
    ):
        self.logger.info(f"Checking for duplicates in {path}")
        if recursive:
            images = [
                p for p in path.rglob("*")
                if p.is_file() and is_image(p)
            ]
        else:
            images = [
                p for p in path.glob("*")
                if p.is_file() and is_image(p)
            ]
        
        with ThreadPoolExecutor(max_workers = 20, thread_name_prefix = "hashing") as executor:
            executor.map(self.hash_image, images)
        
        images = list(self.hashes.items())

        for i, (img_1, hash_1) in enumerate(images):
            if img_1 in self.deleted:
                continue

            for img_2, hash_2 in images[i + 1:]:
                if img_2 in self.deleted:
                    continue

                distance = hash_1 - hash_2
                similarity = 1 - (distance / 64)

                if similarity >= similarity_threshold:
                    # Remove smallest image
                    img_1_size = img_1.stat().st_size
                    img_2_size = img_2.stat().st_size

                    img_1_size_f = format_bytes(img_1_size)
                    img_2_size_f = format_bytes(img_2_size)
                    
                    if img_1_size > img_2_size:
                        img_2.unlink()
                        self.deleted.add(img_2)

                        self.logger.info(
                            "Duplicate Found:\n"
                            f"  Keep ({img_1_size_f}): {img_1}\n"
                            f"  Delete ({img_2_size_f}): {img_2}\n"
                            f"  Similarity: {similarity:.2%}"
                        )
                    
                    else:
                        img_1.unlink()
                        self.deleted.add(img_1)
      
                        self.logger.info(
                            "Duplicate Found:\n"
                            f"  Keep ({img_2_size_f}): {img_2}\n"
                            f"  Delete ({img_1_size_f}): {img_1}\n"
                            f"  Similarity: {similarity:.2%}"
                        )
 
    def clear(self):
        self.hashes = {}
        self.deleted = set()
    
    def hash_image(self, path: Path) -> ImageHash | None:
        with self.lock:
            if path in self.hashes:
                return self.hashes[path]
        
        try:
            with Image.open(path) as img:
                img_hash = imagehash.phash(img)
            
            with self.lock:
                self.hashes[path] = img_hash
            
            self.logger.info(f"Hashed: {path}")
            
            return img_hash
        
        except Exception:
            return None