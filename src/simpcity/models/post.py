from dataclasses import dataclass, field
from datetime import datetime

from .user import User

@dataclass
class Post:
    url: str
    id: int
    posted_at: datetime
    user: User | None = None
    external_urls: list[str] = field(default_factory = list)