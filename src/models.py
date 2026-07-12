from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

@dataclass
class ExternalURL:
    created_at: datetime
    url: str
    domain_name: str
    username: str
    tags: list[str] = field(default_factory = list)

@dataclass
class DownloadResult:
    url: ExternalURL
    path: Path
    size: int