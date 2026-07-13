from dataclasses import dataclass, field
from datetime import datetime

from .user import User

@dataclass
class Post:
    url: str
    id: int
    user: User
    posted_at: datetime
    external_urls: list[str] = field(default_factory = list)