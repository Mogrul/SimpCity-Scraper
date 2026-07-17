import io
import json
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from pathlib import Path

import imagehash
from PIL import Image
from imagehash import ImageHash

from config import Config
from database import Database
from models import MarkedDelete
from util import is_image, format_bytes, is_video

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

    def check_videos(self, path: Path, completed_links: dict[Path, str]) -> None:
        ffmpeg_path = self.config.duplication.ffmpeg_path
        ffprobe_path = self.config.duplication.ffprobe_path

        if not ffmpeg_path.is_file():
            self.logger.error(f"FFMPEG path: {ffmpeg_path} doesn't exist, can't check for video duplicates!")
            return

        if not ffprobe_path.is_file():
            self.logger.error(f"FFProbe path: {ffprobe_path} doesn't exist, can't check for video duplicates!")
            return

        videos = Videos(path, completed_links)
        hash_count = videos.hash_videos()

        if not hash_count:
            self.logger.warning(f"No videos hashed in {path}")
            return

        marked_delete_count = videos.compare_hashes()

        if not marked_delete_count:
            self.logger.info(f"No duplicate videos found in {path}")
            return

        else:
            self.logger.info(f"Found {marked_delete_count} duplicate videos in {path}")

        videos.delete_duplicates()


class Videos:
    def __init__(
            self,
            path: Path,
            completed_links: dict[Path, str]
    ):
        self.logger = logging.getLogger("duplication.videos")
        self.path = path
        self.completed_links = completed_links
        self.config = Config()
        self.database = Database()

        self.hash_cache: dict[Path, list[ImageHash]] = {}
        self.marked_delete: list[MarkedDelete] = []

    def hash_videos(self) -> int:
        if not self.path.exists():
            return 0

        videos = [
            v for v in self.path.rglob("*")
            if v.is_file() and is_video(v)
        ]

        if not videos: return 0

        # Retrieve a hardware accelerator to use
        hwaccel = self.get_best_hwaccel()

        with ThreadPoolExecutor(
            max_workers = self.config.thread_count,
            thread_name_prefix = "duplication.videos.thread"
        ) as executor:
            complete = 0
            futures: dict[Future, Path] = {
                executor.submit(self.hash_video, p, hwaccel): p
                for p in videos
            }

            for future in as_completed(futures.keys()):
                vidpath = futures[future]

                try:
                    vidhashes = future.result()

                except Exception as e:
                    self.logger.error(e)
                    continue

                if not vidhashes:
                    self.logger.error(f"Failed to hash video: {vidpath}")
                    continue

                complete += 1
                self.hash_cache[vidpath] = vidhashes
                self.logger.info(f"{f'{complete}/{len(videos)}':<15} Hashing...")

        return len(self.hash_cache.keys())

    def get_video_duration(self, path: Path) -> float:
        result = subprocess.run(
            [
                str(self.config.duplication.ffprobe_path),
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(path)
            ],
            capture_output = True,
            text = True,
            check = True
        )

        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    def get_best_hwaccel(self) -> str | None:
        available = self.get_hwaccels()

        # Prefer NVIDIA
        if "cuda" in available:
            return "cuda"

        # Windows GPU acceleration fallback
        if "d3d12va" in available:
            return "d3d12va"

        if "d3d11va" in available:
            return "d3d11va"

        # Intel
        if "qsv" in available:
            return "qsv"

        # AMD/Linux
        if "vaapi" in available:
            return "vaapi"

        return None

    def get_hwaccels(self) -> list[str]:
        result = subprocess.run(
            [
                str(self.config.duplication.ffmpeg_path),
                "-hide_banner",
                "-hwaccels"
            ],
            capture_output = True,
            text = True,
            check = True
        )

        lines = result.stdout.splitlines()

        return [
            line.strip()
            for line in lines
            if line.strip() and not line.startswith("Hardware")
        ]

    def get_command(
            self,
            timestamp: float,
            hwaccel: str | None,
            path: Path
    ):
        command = [str(self.config.duplication.ffmpeg_path)]
        if hwaccel: command.extend(["-hwaccel", hwaccel])
        command.extend([
            "-ss", str(timestamp),
            "-i", str(path),
            "-vframes", "1",
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "-loglevel", "error",
            "pipe:1"
        ])

        return command

    def hash_video(self, path: Path, hwaccel: str | None) -> list[ImageHash]:
        hashes: list[ImageHash] = []
        samples = self.config.duplication.samples

        duration = self.get_video_duration(path)

        for i in range(0, samples):
            timestamp = duration * ((i + 1) / (samples + 1))

            result = subprocess.run(
                self.get_command(timestamp, hwaccel, path),
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                check = True
            )

            if result.returncode != 0:
                self.logger.error(result.stderr.decode())
                return []

            image = Image.open(io.BytesIO(result.stdout))
            hashes.append(imagehash.phash(image, hash_size = 4))

        return hashes

    def compare_hashes(self):
        def video_pairs():
            for i, (vid1, hashes1) in enumerate(videos):
                for vid2, hashes2 in videos[i + 1:]:
                    yield i, vid1, vid2, hashes1, hashes2

        videos = list(self.hash_cache.items())
        completed_videos = set()

        with ThreadPoolExecutor(
            max_workers = self.config.thread_count,
            thread_name_prefix = "duplication.videos.thread"
        ) as executor:
            for index, result in executor.map(
                lambda args: self.compare_video(*args),
                video_pairs(),
                buffersize = self.config.thread_count * 4
            ):
                index += 1

                if result:
                    self.marked_delete.append(result)

                if index not in completed_videos:
                    completed_videos.add(index)

                    self.logger.info(f"{f'{len(completed_videos)}/{len(videos)}':<15} Comparing...")

        return len(self.marked_delete)

    def compare_video(
            self,
            index: int,
            vid1: Path,
            vid2: Path,
            hashes1: list[ImageHash],
            hashes2: list[ImageHash]
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

    def delete_duplicates(self):
        deleted_count = 0
        bytes_saved = 0

        while self.marked_delete:
            to_delete = self.marked_delete.pop()

            vid1 = to_delete.file1
            vid2 = to_delete.file2

            try:
                vid1_size = vid1.stat().st_size
                vid2_size = vid2.stat().st_size

            except FileNotFoundError:
                continue

            if vid1_size > vid2_size:
                kept, kept_size = vid1, vid1_size
                deleted, deleted_size = vid2, vid2_size

            else:
                kept, kept_size = vid2, vid2_size
                deleted, deleted_size = vid1, vid1_size

            # Try and get deleted link
            link = self.completed_links.get(deleted, None)
            if link:
                self.database.add_duplicate(link)

            deleted.unlink(missing_ok = True)
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
                buffersize = self.config.thread_count * 4,
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

            deleted.unlink(missing_ok = True)
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

