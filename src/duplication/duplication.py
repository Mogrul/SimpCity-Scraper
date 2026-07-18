import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, FIRST_COMPLETED, Future
from json import JSONDecodeError
from pathlib import Path

import PIL
import imagehash
from PIL import Image
from imagehash import ImageHash
import subprocess

from config import Config
from database import Database
from .models import MarkedDelete, DuplicationResult
from util import is_video, is_image, format_bytes


class Duplication:
    def __init__(self, path: Path, completed_links: dict[Path, str]):
        self.logger = logging.getLogger("Duplication")
        self.config = Config()
        self.path = path
        self.completed_links = completed_links

        if self.config.database.enabled:
            self.database = Database()

    def get_files(self, videos: bool) -> list[Path]:
        files = [f for f in self.path.rglob("*") if f.is_file()]

        if videos:
            return [f for f in files if is_video(f)]
        else:
            return [f for f in files if is_image(f)]

    def check_videos(self) -> DuplicationResult | None:
        videos = self.get_files(True)
        hashed_files = self.hash_files(videos, True)

        if len(hashed_files) == 0:
            self.logger.info(f"Found no video files in {self.path}")
            return None

        else:
            self.logger.info(f"Found {len(videos)} video files in {self.path}")

        marked_delete = self.compare_hashes(hashed_files, True)

        if len(marked_delete) == 0:
            self.logger.info(f"Found no duplicate video files in {self.path}")
            return None

        deleted_count, bytes_saved = self.delete_duplicates(marked_delete)
        return DuplicationResult(
            deleted_count,
            bytes_saved
        )

    def check_images(self) -> DuplicationResult | None:
        images = self.get_files(False)
        hashed_files = self.hash_files(images, False)

        if len(hashed_files) <= 0:
            self.logger.info(f"Found no images in {self.path}")
            return None

        else:
            self.logger.info(f"Found {len(images)} images in {self.path}")

        marked_delete = self.compare_hashes(hashed_files, False)

        if len(marked_delete) <= 0:
            self.logger.info(f"Found no duplicate images in {self.path}")
            return None

        deleted_count, bytes_saved = self.delete_duplicates(marked_delete)
        return DuplicationResult(
            deleted_count,
            bytes_saved
        )

    def hash_files(self, files: list[Path], videos: bool = False) -> dict[Path, list[ImageHash]]:
        hashed_files: dict[Path, list[ImageHash]] = {}
        hashing_fnc = self.hash_image if not videos else self.hash_video
        type_str = "video" if videos else "image"

        with ThreadPoolExecutor(
            max_workers = self.config.thread_count,
            thread_name_prefix = "hashing.thread"
        ) as executor:
            log_every = max(1, len(files) // 20)
            complete = 0
            futures: dict[Future, Path] = {
                executor.submit(hashing_fnc, file): file
                for file in files
            }

            for future in as_completed(futures):
                file_path = futures[future]

                try:
                    hashes = future.result()

                except Exception as e:
                    self.logger.error(e)
                    continue

                if not hashes:
                    self.logger.error(f"Failed to hash {type_str} file: {file_path}")
                    continue

                complete += 1
                hashed_files[file_path] = hashes
                if complete % log_every == 0 or complete == len(files):
                    self.logger.info(f"{f'{complete}/{len(files)}':<15} hashing {type_str} files")

        return hashed_files

    def compare_hashes(self, hashed_files: dict[Path, list[ImageHash]], video: bool) -> list[MarkedDelete]:
        def file_pairs():
            for i, (file1, hashes1) in enumerate(files):
                for file2, hashes2 in files[i + 1 :]:
                    yield i, file1, file2, hashes1, hashes2

        compare_fnc = self.compare_image if not video else self.compare_video
        marked_deletes: list[MarkedDelete] = []
        files = list(hashed_files.items())
        type_str = "video" if video else "image"

        with ThreadPoolExecutor(
            max_workers = self.config.thread_count,
            thread_name_prefix = "comparing.thread"
        ) as executor:
            completed_files: set[int] = set() # Store completed indexes for logging
            log_every = max(1, len(files) // 20)

            for index, result in executor.map(
                lambda args: compare_fnc(*args),
                file_pairs(),
                buffersize = self.config.thread_count * 4
            ):
                index += 1

                if result:
                    marked_deletes.append(result)

                if index not in completed_files:
                    completed_files.add(index)
                    if len(completed_files) % log_every == 0 or len(completed_files) == len(files):
                        self.logger.info(
                            f"{f'{len(completed_files)}/{len(files)}':<15} comparing {type_str} files"
                        )

        return marked_deletes

    def hash_image(self, img_path: Path) -> list[ImageHash] | None:
        try:
            with Image.open(img_path) as img:
                return [imagehash.phash(img, hash_size = 4)]

        except (FileNotFoundError, PIL.UnidentifiedImageError):
            return None

    def hash_video(self, vid_path: Path) -> list[ImageHash] | None:
        hashes: list[ImageHash] = []
        samples = self.config.duplication.samples

        # Obtain video duration for timestamping
        result = subprocess.run(
            [
                str(self.config.duplication.ffprobe_path),
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(vid_path)
            ],
            capture_output = True,
            text = True,
            check = True
        )

        try:
            data = json.loads(result.stdout)

        except JSONDecodeError:
            return hashes

        duration: float = float(data["format"]["duration"])

        # Recurse through target samples to obtain frames
        for i in range(0, samples):
            timestamp = duration * ((i + 1) / (samples + 1))

            # Get the image frame as bytes object
            result = subprocess.run(
                [
                    str(self.config.duplication.ffmpeg_path),
                    "-ss", str(timestamp),
                    "-i", str(vid_path),
                    "-vframes", "1",
                    "-f", "image2pipe",
                    "-vcodec", "mjpeg",
                    "-loglevel", "error",
                    "pipe:1"
                ],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                check = True
            )

            if result.returncode != 0:
                self.logger.error(result.stderr.decode("utf-8"))
                return []

            image = Image.open(io.BytesIO(result.stdout))
            hashes.append(imagehash.phash(image, hash_size = 4))

        return hashes

    def compare_image(
            self,
            index: int,
            img1: Path,
            img2: Path,
            hashes1: list[ImageHash],
            hashes2: list[ImageHash],
    ) -> tuple[int, MarkedDelete | None]:
        marked_delete = None
        hash1 = hashes1[0]
        hash2 = hashes2[0]
        hash_size = hash1.hash.size
        similarity = (
            1 - ((hash1 - hash2) / hash_size)
        )

        if similarity >= self.config.duplication.threshold:
            marked_delete = MarkedDelete(img1, img2)

        return index, marked_delete

    def compare_video(
            self,
            index: int,
            vid1: Path,
            vid2: Path,
            hashes1: list[ImageHash],
            hashes2: list[ImageHash],
    ) -> tuple[int, MarkedDelete | None]:
        marked_delete = None

        if len(hashes1) != len(hashes2):
            return index, marked_delete

        hash_size = hashes1[0].hash.size
        similarity = (
            sum(
                1 - ((hash1 - hash2) / hash_size)
                for hash1, hash2 in zip(hashes1, hashes2)
            )
            / len(hashes1)
        )

        if similarity >= self.config.duplication.threshold:
            marked_delete = MarkedDelete(vid1, vid2)

        return index, marked_delete

    def delete_duplicates(
            self,
            marked_delete: list[MarkedDelete]
    ) -> tuple[int, int]:
        deleted_count = 0
        bytes_saved = 0

        while marked_delete:
            to_delete = marked_delete.pop()
            file1 = to_delete.file1
            file2 = to_delete.file2

            try:
                file1_size = file1.stat().st_size
                file2_size = file2.stat().st_size

            except FileNotFoundError:
                continue

            if file1_size > file2_size:
                kept, kept_size = file1, file1_size
                deleted, deleted_size = file2, file2_size

            else:
                kept, kept_size = file2, file2_size
                deleted, deleted_size = file1, file1_size

            # Try and get original link of downloaded file
            link = self.completed_links.get(deleted, None)
            if link and getattr(self, "database", False):
                self.database.add_duplicate(link)

            deleted.unlink()
            deleted_count += 1
            bytes_saved += int(deleted_size)
            self.logger.info(
                "Duplicate Found:\n"
                f"          {format_bytes(deleted_size):<10} deleted {deleted}\n"
                f"         {format_bytes(kept_size):<10} kept {kept}"
            )

        return deleted_count, bytes_saved