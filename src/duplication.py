import threading
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from tqdm import tqdm

from PIL import Image
import imagehash
import cv2
from imagehash import ImageHash

from .util import is_image, format_bytes, is_video
from src.shared.config import Config

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
        self.config = Config()
        self.max_pending = self.config.workers * 100
        
        self.image_hashes: dict[Path, ImageHash] = {}
        self.image_hash_lock = threading.Lock()
        self.deleted_images = set()
        
        self.video_hashes: dict[Path, list[ImageHash]] = {}
        self.video_hash_lock = threading.Lock()
        self.deleted_videos = set()
        
        self._initialised = True

    def check_duplicate_images(
            self,
            path: Path,
            recursive = True
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
        
        if not images:
            self.logger.info(f"No images found in {path}")
            return
        
        with ThreadPoolExecutor(
                max_workers = self.config.workers * 10,
                thread_name_prefix = "duplication.hashing.image"
        ) as executor:
            futures = [
                executor.submit(self.hash_image, image)
                for image in images
            ]
            
            with tqdm(
                    total = len(images),
                    desc = "Hashing images"
            ) as progress:
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    
                    except Exception as e:
                        self.logger.info(f"Failed to hash image: {e}")
                        progress.update(1)
                        continue
                        
                    progress.update(1)
        
        images = list(self.image_hashes.items())
        to_delete: list[dict] = []
        
        self.logger.info(f"Comparing hashes...")
        with ThreadPoolExecutor(
            max_workers = self.config.workers * 10,
            thread_name_prefix = "duplication.comparison.image"
        ) as executor:

            futures = set()

            with tqdm(
                total=len(images) * (len(images) - 1) // 2,
                desc="Comparing image hashes"
            ) as progress:

                for i, (img_1, hash_1) in enumerate(images):
                    if img_1 in self.deleted_images:
                        continue

                    for img_2, hash_2 in images[i + 1:]:
                        if img_2 in self.deleted_images:
                            continue

                        futures.add(
                            executor.submit(
                                self._compare_image_pairs,
                                img_1,
                                hash_1,
                                img_2,
                                hash_2
                            )
                        )

                        # Wait until some work finishes before adding more
                        if len(futures) >= self.max_pending:
                            done, futures = wait(
                                futures,
                                return_when = FIRST_COMPLETED
                            )

                            for future in done:
                                try:
                                    result = future.result()
                                    if result is not None:
                                        to_delete.append(result)

                                except Exception as e:
                                    self.logger.error(
                                        f"Error comparing image hashes: {e}"
                                    )

                                progress.update(1)

                # Finish remaining futures
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result is not None:
                            to_delete.append(result)

                    except Exception as e:
                        self.logger.error(
                            f"Error comparing image hashes: {e}"
                        )

                    progress.update(1)
        
        deleted_count = 0
        
        for result in to_delete:
            deleted = result["deleted"]
            to_delete_path = deleted["path"]
            to_delete_size = deleted["size"]
            
            kept = result["kept"]
            kept_path = kept["path"]
            kept_size = kept["size"]
            
            similarity = result["similarity"]
            
            self.logger.info(
                "Duplicate found:\n"
                "  Deleting:\n"
                f"      Path: {to_delete_path}\n"
                f"      Size: {format_bytes(to_delete_size)}\n"
                "  Keeping:\n"
                f"      Path: {kept_path}\n"
                f"      Size: {format_bytes(kept_size)}"
                f"  Similarity: {similarity * 100}%"
            )
            
            try:
                to_delete_path.unlink()
                self.deleted_images.add(to_delete_path)
                deleted_count += 1
            
            except Exception as e:
                self.logger.error(f"Error deleting path: {deleted} {e}")
                continue
        
        if deleted_count == 0:
            self.logger.info(f"Found no duplicate images")
        
        else:
            self.logger.info(f"Deleted {deleted_count} images")
 
    def check_duplicate_videos(
            self,
            path: Path,
            recursive = True
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
        
        if not videos:
            self.logger.info(f"No videos found in {path}")
            return
        
        with ThreadPoolExecutor(
                max_workers = self.config.workers,
                thread_name_prefix = "duplication.hashing.video"
        ) as executor:
            futures = [
                executor.submit(self.hash_video, video)
                for video in videos
            ]
            
            with tqdm(
                    total = len(videos),
                    desc = "Hashing videos"
            ) as progress:
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    
                    except Exception as e:
                        self.logger.info(f"Failed to hash video: {e}")
                        progress.update(1)
                        continue
                    
                    progress.update(1)

        videos = list(self.video_hashes.items())
        to_delete: list[dict] = []
        
        self.logger.info(f"Comparing hashes...")
        with ThreadPoolExecutor(
                max_workers = self.config.workers,
                thread_name_prefix = "duplication.comparison.video"
        ) as executor:
            futures = set()
            
            with tqdm(
                total = len(videos) * (len(videos) - 1) // 2,
                desc = "Comparing video hashes"
            ) as progress:
                for i, (vid_1, hashes_1) in enumerate(videos):
                    if vid_1 in self.deleted_videos:
                        continue
                    
                    for vid_2, hashes_2 in videos[i + 1:]:
                        if vid_2 in self.deleted_videos:
                            continue
                        
                        futures.add(
                            executor.submit(
                                self._compare_video_pairs,
                                vid_1,
                                hashes_1,
                                vid_2,
                                hashes_2
                            )
                        )
                        
                        # Wait until some work finishes before adding more
                        
                        if len(futures) >= self.max_pending:
                            done, futures = wait(
                                futures,
                                return_when = FIRST_COMPLETED
                            )
                            
                            for future in done:
                                try:
                                    result = future.result()
                                    
                                    if result is not None:
                                        to_delete.append(result)
                                
                                except Exception as e:
                                    self.logger.error(
                                        f"Error comparing video hashes: {e}"
                                    )
                                
                                progress.update(1)
                
                # Finish remaining
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result is not None:
                            to_delete.append(result)
                        
                    except Exception as e:
                        self.logger.error(
                            f"Error comparing video hashes: {e}"
                        )
                    
                    progress.update(1)

        deleted_count = 0
        
        for result in to_delete:
            deleted = result["deleted"]
            to_delete_path = deleted["path"]
            to_delete_size = deleted["size"]
            
            kept = result["kept"]
            kept_path = kept["path"]
            kept_size = kept["size"]
            
            similarity = result["similarity"]
            
            self.logger.info(
                "Duplicate found:\n"
                "  Deleting:\n"
                f"      Path: {to_delete_path}\n"
                f"      Size: {format_bytes(to_delete_size)}\n"
                "  Keeping:\n"
                f"      Path: {kept_path}\n"
                f"      Size: {format_bytes(kept_size)}"
                f"  Similarity: {similarity * 100}%"
            )
            
            try:
                to_delete_path.unlink()
            
                self.deleted_videos.add(to_delete_path)
                deleted_count += 1
            
            except Exception as e:
                self.logger.error(f"Error deleting path: {deleted} {e}")
                continue
            
        if deleted_count == 0:
            self.logger.info(f"Found no duplicate videos")
        
        else:
            self.logger.info(f"Deleted {deleted} videos")
 
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
    
    def _compare_video_pairs(
            self,
            vid_1: Path,
            hashes_1: list[ImageHash],
            vid_2: Path,
            hashes_2: list[ImageHash]
    ) -> dict | None:
        if len(hashes_1) != len(hashes_2):
            return None
            
        average_similarity = (
            sum(
                1 - ((h1 - h2) / 64)
                for h1, h2 in zip(hashes_1, hashes_2)
            )
            / len(hashes_1)
        )
        
        if average_similarity < self.config.similarity_threshold:
            return None
        
        vid_1_size = vid_1.stat().st_size
        vid_2_size = vid_2.stat().st_size

        if vid_1_size > vid_2_size:
            deleted, kept = (vid_2, vid_2_size), (vid_1, vid_1_size)
        else:
            deleted, kept = (vid_1, vid_1_size), (vid_2, vid_2_size)

        return {
            "deleted": {
                "path": deleted[0],
                "size": deleted[1],
            },
            "kept": {
                "path": kept[0],
                "size": kept[1],
            },
            "similarity": average_similarity,
        }
    
    def _compare_image_pairs(
            self,
            img_1: Path,
            hash_1: ImageHash,
            img_2: Path,
            hash_2: ImageHash
    ) -> dict | None:
        similarty = (
            1 - ((
                hash_1 - hash_2
            ) / 64)
        )
        
        if similarty < self.config.similarity_threshold:
            return None
        
        img_1_size = img_1.stat().st_size
        img_2_size = img_2.stat().st_size
        
        if img_1_size > img_2_size:
            deleted, kept = (img_2, img_2_size), (img_1, img_1_size)
        else:
            deleted, kept = (img_1, img_1_size), (img_2, img_2_size)
        
        return {
            "deleted": {
                "path": deleted[0],
                "size": deleted[1]
            },
            "kept": {
                "path": kept[0],
                "size": kept[1]
            },
            "similarity": similarty
        }