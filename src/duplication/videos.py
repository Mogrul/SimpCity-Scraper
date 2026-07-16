import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

import imagehash
from imagehash import ImageHash
from PIL import Image
import ffmpeg

from .models import ToDelete
from src.database.database import Database
from src.database.models import DuplicateItem
from src.shared import Config

class VideoDuplication:
    def __init__(self, videos_path: Path):
        self._logger = logging.getLogger("duplication.videos")
        self._config = Config()
        self._videos_path = videos_path
        self._max_pending = self._config.network.workers * 4
        self._database = Database()
        
        self._hashes: dict[Path, list[ImageHash]] = {}
        self._to_delete: list[ToDelete] = []
    
    def run(self):
        # Hash all videos
        self.hash_videos()
        if not self._hashes:
            self._logger.warning(f"No videos found in hashes")
            return
        
        # Compare the video hashes
        self.compare_videos()
        
        if not self._to_delete:
            self._logger.warning(f"No duplicate videos found")
            return
        
        else:
            self._logger.info(f"Found {len(self._to_delete)} duplicate videos, deleteing..")
        
        self.deleted_duplicates()
    
    def hash_videos(self):
        path = self._videos_path
        
        if not path.exists():
            self._logger.warning(f"Path doesn't exist: {path}")
        
        videos = [
            v for v in path.rglob("*")
            if v.is_file() and self._is_video(v)
        ]
        
        if not videos:
            self._logger.warning(f"No videos found in {path}")
            return
        
        # Hash the images with a thread pool.
        complete = 0
        with ThreadPoolExecutor(
                self._config.network.workers,
                "duplication.videos.hashing"
        ) as executor:
            futures = [
                executor.submit(self._hash_video, video)
                for video in videos
            ]
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                
                except Exception as e:
                    # Exception caught
                    self._logger.error(f"Error hashing video: {e}")
                    continue
                
                video_path, video_hashes = result
                
                # Nothing hashed
                if not video_hashes: continue
                self._hashes[video_path] = video_hashes
                complete += 1
                
                self._logger.info(f"{f'{complete}/{len(videos)}':>16} Hashed {video_path}")
    
    def compare_videos(self):
        def video_pairs():
            for i, (vid_1, hashes_1) in enumerate(videos):
                for vid_2, hashes_2, in videos[i + 1:]:
                    yield i, vid_1, hashes_1, vid_2, hashes_2
        
        videos = list(self._hashes.items())
        completed_videos = set()
        with ThreadPoolExecutor(
                max_workers = self._config.network.workers,
                thread_name_prefix = "duplication.videos.comparing"
        ) as executor:
            for index, result in executor.map(
                lambda args: self._compare_video_pairs(*args),
                video_pairs(),
                buffersize = self._max_pending
            ):
                index += 1
                
                if result:
                    self._to_delete.append(result)
                
                if index not in completed_videos:
                    completed_videos.add(index)
                    
                    self._logger.info(
                        f"{f'{len(completed_videos)}/{len(videos)}':>16} Comparing video hashes"
                    )
    
    def deleted_duplicates(self):
        delete_count = 0
        saved_bytes = 0
        
        for to_delete in self._to_delete:
            vid_1 = to_delete.file_1
            vid_2 = to_delete.file_2
            similarity = to_delete.similarity
            
            try:
                vid_1_size = vid_1.stat().st_size
                vid_2_size = vid_2.stat().st_size
            
            except FileNotFoundError:
                continue
            
            if vid_1_size > vid_2_size:
                kept, kept_size = vid_1, vid_1_size
                deleted, deleted_size = vid_2, vid_2_size
            
            else:
                kept, kept_size = vid_2, vid_2_size
                deleted, deleted_size = vid_1, vid_1_size
            
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
    
    def _hash_video(self, path: Path) -> tuple[Path, list[ImageHash]]:
        hashes: list[ImageHash] = []
        samples = self._config.duplication.samples
        
        # Get video duration
        probe = ffmpeg.probe(str(path))
        duration = float(
            next(
                stream for stream in probe["streams"]
                if stream["codec_type"] == "video"
            )["duration"]
        )
        
        for i in range(0, samples):
            timestamp = duration * ((i + 1) / (samples + 1))
            
            out, _ = (
                ffmpeg
                .input(
                    str(path),
                    ss = timestamp,
                    hwaccel = "cuda"
                )
                .output(
                    "pipe:",
                    vframes = 1,
                    format = "image2",
                    vcodec = "mjpeg",
                    loglevel="error"
                )
                .run(
                    capture_stdout = True,
                    capture_stderr = True
                )
            )

            img = Image.open(io.BytesIO(out))
            img_hash = imagehash.phash(img)
            
            hashes.append(img_hash)
        
        return path, hashes
    
    def _compare_video_pairs(
            self,
            index: int,
            vid_1: Path,
            hashes_1: list[ImageHash],
            vid_2: Path,
            hashes_2: list[ImageHash]
    ) -> tuple[int, ToDelete | None]:
        result = None
        
        if len(hashes_1) != len(hashes_2):
            return (index, result)
        
        hash_size = hashes_1[0].hash.size
        similarity = (
            sum(
                1 - ((hash_1 - hash_2) / hash_size)
                for hash_1, hash_2 in zip(hashes_1, hashes_2)
            )
            / len(hashes_1)
        )
        
        if similarity >= self._config.duplication.threshold:
            result = ToDelete(
                file_1 = vid_1,
                file_2 = vid_2,
                similarity = similarity
            )
        
        return index, result
        
    def _is_video(self, path: Path):
        if not path.is_file():
            return False
        
        video_extensions = {
            ".mp4", ".mkv", ".avi", ".mov",
            ".webm", ".wmv", ".flv",
            ".m4v", ".mpeg", ".mpg"
        }
        
        if path.suffix.lower() in video_extensions:
            return True
        
        return False
    
    def _format_bytes(self, amount: int) -> str:
        value = float(amount)
    
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if value < 1024:
                return f"{value:.2f} {unit}"
                    
            value /= 1024

        return f"{value:.2f} PB"