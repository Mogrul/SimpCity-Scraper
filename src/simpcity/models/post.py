from dataclasses import dataclass, field
from datetime import datetime

from .external_url import ExternalURL

@dataclass
class Post:
    url: str
    id: int
    posted: datetime
    external_urls: list[ExternalURL] = field(default_factory = list)