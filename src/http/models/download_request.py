from dataclasses import dataclass
from pathlib import Path

@dataclass
class HttpDownloadRequest:
    url: str
    destination: Path
    referer: str | None = None
    origin: str | None = None