import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from pathlib import Path

import imagehash
from PIL import Image
from imagehash import ImageHash

from config import Config
from database import Database
from models import MarkedDelete
from util import is_image, format_bytes


class Duplication:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger("Duplication")

    def check_images(self, path: Path, completed_links: dict[Path, str]) -> None:
        images = Images(path, completed_links)
        hashed_count = images.hash_images()

        if not hashed_count:
            self.logger.warning(f"No images hashed in {path}")
            return

        marked_delete_count = images.compare_hashes()

        if not marked_delete_count:
            self.logger.info(f"No duplicate images found in {path}")
            return

        else:
            self.logger.info(f"Found {marked_delete_count} duplicate images in {path}")

        images.delete_duplicates()

def hash_image(path: Path) -> ImageHash | None:
    try:
        with Image.open(path) as image:
            imghash = imagehash.phash(image, hash_size = 4)

        return imghash

    except Exception:
        return None

class Images:
    def __init__(self, path: Path, completed_links: dict[Path, str]) -> None:
        self.logger = logging.getLogger("Duplication.Images")
        self.path = path
        self.completed_links = completed_links
        self.config = Config()
        self.database = Database()

        self.hash_cache: dict[Path, ImageHash] = {}
        self.marked_delete: list[MarkedDelete] = []

    def hash_images(self) -> int:
        if not self.path.exists():
            return 0

        images = [
            i for i in self.path.rglob("*")
            if i.is_file() and is_image(i)
        ]

        if not images: return 0

        with ThreadPoolExecutor(
            max_workers = self.config.thread_count,
            thread_name_prefix = "duplication.images.thread"
        ) as executor:
            complete = 0
            futures: dict[Future, Path] = {
                executor.submit(hash_image, p): p
                for p in images
            }

            for future in as_completed(futures.keys()):
                imgpath = futures[future]

                try:
                    imghash = future.result()

                except Exception as e:
                    self.logger.error(e)
                    continue

                if not imghash:
                    self.logger.error(f"Failed to hash image: {imgpath}")
                    continue

                complete += 1
                self.hash_cache[imgpath] = imghash
                self.logger.info(f"{f'{complete}/{len(images)}':<15} Hashing...")

        return len(self.hash_cache)

    def compare_hashes(self) -> int:
        def image_pairs():
            for i, (img1, hash1) in enumerate(images):
                for img2, hash2 in images[i + 1:]:
                    yield i, img1, img2, hash1, hash2

        images = list(self.hash_cache.items())
        completed_images = set()

        with ThreadPoolExecutor(
            max_workers = self.config.thread_count,
            thread_name_prefix = "duplication.images.thread"
        ) as executor:
            for index, result in executor.map(
                lambda args: self.compare_image(*args),
                image_pairs(),
                buffersize = self.config.thread_count * 2,
            ):
                index += 1

                if result:
                    self.marked_delete.append(result)

                if index not in completed_images:
                    completed_images.add(index)

                    self.logger.info(f"{f'{len(completed_images)}/{len(images)}':<15} Comparing images")

        return len(self.marked_delete)

    def compare_image(
            self,
            index: int,
            img1: Path,
            img2: Path,
            hash1: ImageHash,
            hash2: ImageHash
    ) -> tuple[int, MarkedDelete | None]:
        marked_delete = None
        hash_size = hash1.hash.size
        similarity = (
                1 - ((hash1 - hash2) / hash_size)
        )

        if similarity >= self.config.duplication.threshold:
            marked_delete = MarkedDelete(img1, img2)

        return index, marked_delete

    def delete_duplicates(self):
        deleted_count = 0
        bytes_saved = 0

        while self.marked_delete:
            to_delete = self.marked_delete.pop()

            img1 = to_delete.file1
            img2 = to_delete.file2

            try:
                img1_size = img1.stat().st_size
                img2_size = img2.stat().st_size

            except FileNotFoundError:
                continue

            if img1_size > img2_size:
                kept, kept_size = img1, img1_size
                deleted, deleted_size = img2, img2_size

            else:
                kept, kept_size = img2, img2_size
                deleted, deleted_size = img1, img1_size

            # Try and get deleted link
            link = self.completed_links.get(deleted, None)
            if link:
                self.database.add_duplicate(link)
                pass

            deleted.unlink()
            deleted_count += 1
            bytes_saved += deleted_size
            self.logger.info(
                "Duplicate Found:\n"
                f"          {format_bytes(deleted_size):<10} Deleted {deleted}\n"
                f"          {format_bytes(kept_size):<10} Kept {kept}\n"
            )

        self.logger.info(
            "Complete:\n"
            f"          {format_bytes(bytes_saved):<10} saved\n"
            f"          {deleted_count:<10} deleted\n"
        )

