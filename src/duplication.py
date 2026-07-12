import threading
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor

from PIL import Image
import imagehash
import cv2
from imagehash import ImageHash

from .util import is_image, format_bytes, is_video

class Duplication:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        
        return cls._instance
    
    def __init__(self):
        if getattr(self, "_initialised", False):
            return
        
        self.logger = logging.getLogger("duplication")
        
        self.image_hashes: dict[Path, ImageHash] = {}
        self.image_hash_lock = threading.Lock()
        self.deleted_images = set()
        
        self.video_hashes = {}
        self.video_hash_lock = threading.Lock()
        self.deleted_videos = set()
        
        self._initialised = True

    def check_duplicate_images(
            self,
            path: Path,
            recursive = True,
            similarity_threshold = 0.90
    ):
        if not path.exists():
            return
        
        self.logger.info(f"Checking for image duplicates in {path}")
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
        
        with ThreadPoolExecutor(
                max_workers = 20,
                thread_name_prefix = "hashing.image"
        ) as executor:
            executor.map(self.hash_image, images)
        
        images = list(self.image_hashes.items())

        for i, (img_1, hash_1) in enumerate(images):
            if img_1 in self.deleted_images:
                continue

            for img_2, hash_2 in images[i + 1:]:
                if img_2 in self.deleted_images:
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
                        self.deleted_images.add(img_2)

                        self.logger.info(
                            "Duplicate Found:\n"
                            f"  Keep ({img_1_size_f}): {img_1}\n"
                            f"  Delete ({img_2_size_f}): {img_2}\n"
                            f"  Similarity: {similarity:.2%}"
                        )
                    
                    else:
                        img_1.unlink()
                        self.deleted_images.add(img_1)
      
                        self.logger.info(
                            "Duplicate Found:\n"
                            f"  Keep ({img_2_size_f}): {img_2}\n"
                            f"  Delete ({img_1_size_f}): {img_1}\n"
                            f"  Similarity: {similarity:.2%}"
                        )
 
    def check_duplicate_videos(
            self,
            path: Path,
            recursive = True,
            similarity_threshold = 0.90
    ):
        if not path.exists():
            return
        
        self.logger.info(f"Checking for video duplicates in {path}")
        if recursive:
            videos = [
                p for p in path.rglob("*")
                if p.is_file() and is_video(p)
            ]
        else:
            videos = [
                p for p in path.glob("*")
                if p.is_file() and is_video(p)
            ]
        
        with ThreadPoolExecutor(
                max_workers = 20,
                thread_name_prefix = "hashing.video"
        ) as executor:
            executor.map(self.hash_video, videos)
        
        videos = list(self.video_hashes.items())
 
    def clear(self):
        self.image_hashes = {}
        self.deleted_images = set()
        
        self.video_hashes = {}
        self.deleted_videos = set()
    
    def hash_image(self, path: Path) -> ImageHash | None:
        with self.image_hash_lock:
            if path in self.image_hashes:
                return self.image_hashes[path]
        
        try:
            with Image.open(path) as img:
                img_hash = imagehash.phash(img)
            
            with self.image_hash_lock:
                self.image_hashes[path] = img_hash
            
            self.logger.info(f"Hashed: {path}")
            
            return img_hash
        
        except Exception:
            return None
    
    def hash_video(self, path: Path, samples = 3) -> list[ImageHash] | None:
        with self.video_hash_lock:
            if path in self.video_hashes:
                return self.video_hashes[path]
        
        hashes: list[ImageHash] = []
        
        try:
            cap = cv2.VideoCapture(str(path))
            
            if not cap.isOpened():
                return None
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            for i in range(samples):
                frame_index = int(frame_count * ((i * 1) / (samples + 1)))
                
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                
                success, frame = cap.read()
                
                if not success:
                    continue
                
                # Convert BGR -> RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                
                hashes.append(imagehash.phash(img))
            
            cap.release()
        
        except Exception as e:
            self.logger.error(f"Failed to hash video {path}: {e}")
        
        with self.video_hash_lock:
            self.video_hashes[path] = hashes
        
        return hashes