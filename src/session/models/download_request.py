from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DownloadRequest:
    link: str
    destination: Path
    headers: dict[str, str] = field(default_factory = dict)
    params: dict[str, str] = field(default_factory = dict)