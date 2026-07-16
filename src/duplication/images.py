import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image
import imagehash
from imagehash import ImageHash

from .models import ToDelete
from src.database.database import Database
from src.database.models import DuplicateItem
from src.shared import Config

class ImageDuplication:
    def __init__(self, images_path: Path):
        self._logger = logging.getLogger("duplication.images")
        self._config = Config()
        self._images_path = images_path
        self._max_pending = self._config.network.workers * 4
        self._database = Database()
        
        self._hashes: dict[Path, ImageHash] = {}
        self._to_delete: list[ToDelete] = []
    
    def run(self):
        # Hash all images
        result = self.hash_images()
        if not result or not self._hashes:
            self._logger.warning(f"No images found in hashes")
            return
        
        hashing_errored, hashing_complete, hashing_total = result
        
        # Compare the images
        self.compare_images()
        
        if not self._to_delete:
            self._logger.warning(f"No duplicate images found")
            return
        
        else:
            self._logger.info(f"Found {len(self._to_delete)} duplicate images, deleting...")
        
        # Delete found duplicates
        self.delete_duplicates()
    
    def hash_images(self) -> tuple[int, ...] | None:
        path = self._images_path
        
        if not path.exists():
            self._logger.warning(f"Path doesn't exist: {path}")
            return
        
        images = [
            p for p in path.rglob("*")
            if p.is_file() and self._is_image(p)
        ]
        
        if not images:
            self._logger.warning(f"No images found in {path}")
            return
        
        # Hash the images with a thread pool.
        errored = 0
        complete = 0
        with ThreadPoolExecutor(
                self._config.network.workers,
                "duplication.images.hashing"
        ) as executor:
            futures = [
                executor.submit(self._hash_image, image)
                for image in images
            ]
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                
                except:
                    errored += 1
                    continue
                
                if not result:
                    errored += 1
                    continue
                
                image_path, image_hash = result
                self._hashes[image_path] = image_hash
                complete += 1
                self._logger.info(f"{f'{complete}/{len(images)}':>16} Hashed {image_path}")

        return (errored, complete, len(images))
        
    def compare_images(self):
        def image_pairs():
            for i, (img_1, hash_1) in enumerate(images):
                for img_2, hash_2 in images[i + 1:]:
                    yield i, img_1, hash_1, img_2, hash_2
        
        images = list(self._hashes.items())
        completed_images = set()
        with ThreadPoolExecutor(
                max_workers = self._config.network.workers,
                thread_name_prefix = "duplication.images.comparing"
        ) as executor:
            for index, result in executor.map(
                lambda args: self._compare_image_pairs(*args),
                image_pairs(),
                buffersize = self._max_pending
            ):
                index += 1
                
                if result:
                    self._to_delete.append(result)
                
                if index not in completed_images:
                    completed_images.add(index)
    
                    self._logger.info(
                        f"{f'{len(completed_images)}/{len(images)}':>16} Comparing hashes"
                    )
    
    def delete_duplicates(self):
        delete_count = 0
        saved_bytes = 0
        
        for to_delete in self._to_delete:
            img_1 = to_delete.file_1
            img_2 = to_delete.file_2
            similarity = to_delete.similarity
            
            try:
                img_1_size = img_1.stat().st_size
                img_2_size = img_2.stat().st_size
            
            except FileNotFoundError:
                continue
            
            if img_1_size > img_2_size:
                kept, kept_size = img_1, img_1_size
                deleted, deleted_size = img_2, img_2_size
                
            else:
                kept, kept_size = img_2, img_2_size
                deleted, deleted_size = img_1, img_1_size
            
            # Delete smallest file
            deleted.unlink()
            saved_bytes += deleted_size
            
            duplicate_item = DuplicateItem(
                kept_path = kept,
                deleted_path = deleted,
                kept_size = kept_size,
                deleted_size = deleted_size,
                similarity = similarity
            )
            self._database.add_duplicate(duplicate_item)
            
            delete_count += 1
            self._logger.info(
                "\n"
                "Duplicate Found:\n"
                f"      {self._format_bytes(deleted_size):>10} Deleted {deleted}\n"
                f"      {self._format_bytes(kept_size):>10} Kept: {kept}"
            )
        
        self._logger.info(
            "\n"
            "Complete:\n"
            f"      {self._format_bytes(saved_bytes)} saved\n"
            f"      {delete_count} deleted"
        )
    
    def _is_image(self, path: Path) -> bool:
        if not path.is_file():
            return False
        
        img_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        
        if path.suffix.lower() in img_extensions:
            return True
        
        return False
    
    def _hash_image(self, path: Path) -> tuple[Path, ImageHash] | None:
        try:
            with Image.open(path) as img:
                img_hash = imagehash.phash(img, hash_size = 4)
            
            return (path, img_hash)
        
        except Exception:
            return None
    
    def _compare_image_pairs(
            self,
            index: int,
            img_1: Path,
            hash_1: ImageHash,
            img_2: Path,
            hash_2: ImageHash
    ) -> tuple[int, ToDelete | None]:
        hash_size = hash_1.hash.size
        similarty = (
            1 - ((
                hash_1 - hash_2
            ) / hash_size)
        )
        
        result = None
        if similarty >= self._config.duplication.threshold:
            result = ToDelete(
                file_1 = img_1,
                file_2 = img_2,
                similarity = similarty
            )
        
        return index, result
    
    def _format_bytes(self, amount: int) -> str:
        value = float(amount)
    
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if value < 1024:
                return f"{value:.2f} {unit}"
                    
            value /= 1024

        return f"{value:.2f} PB"