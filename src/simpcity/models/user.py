from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class User:
    id: int
    url: str
    username: str
    joined_at: datetime
    post_count: int
    reactions_received: int
    avatar_url: str | None = None
    banners: list[str] = field(default_factory = list)