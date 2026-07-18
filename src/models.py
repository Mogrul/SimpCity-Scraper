from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class DownloadConfig:
    location: Path
    skip_domains: list[str] = field(default_factory = list)

@dataclass
class NetworkConfig:
    timeout: int
    chunk_size: int
    cookies: Path
    headers: dict = field(default_factory = dict)

@dataclass
class DuplicationConfig:
    images: bool
    videos: bool
    ffmpeg_path: Path
    ffprobe_path: Path
    threshold: float
    samples: int

@dataclass
class DatabaseConfig:
    enabled: bool
    location: Path

@dataclass
class DuplicationResult:
    deleted_count: int
    bytes_saved: int

    def __iadd__(self, other: "DuplicationResult") -> DuplicationResult:
        self.bytes_saved += other.bytes_saved
        self.deleted_count += other.deleted_count

        return self

@dataclass
class MarkedDelete:
    file1: Path
    file2: Path