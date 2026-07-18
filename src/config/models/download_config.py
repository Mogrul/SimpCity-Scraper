from dataclasses import field, dataclass
from pathlib import Path


@dataclass
class DownloadConfig:
    location: Path
    skip_domains: list[str] = field(default_factory = list)