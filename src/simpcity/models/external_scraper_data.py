from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ExternalScraperData:
    domain: str
    username: str
    url: str
    posted_at: datetime
    file_name: str | None = None
    tags: list[str] = field(default_factory = list)