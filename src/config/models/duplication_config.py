from dataclasses import dataclass
from pathlib import Path


@dataclass
class DuplicationConfig:
    images: bool
    videos: bool
    ffmpeg_path: Path
    ffprobe_path: Path
    threshold: float
    samples: int