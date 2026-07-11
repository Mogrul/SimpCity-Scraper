from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4, UUID

@dataclass
class Post:
    created_at: datetime
    id: UUID = field(default_factory = uuid4)
    external_links: dict[str, list[str]] = field(default_factory = dict)

@dataclass
class Thread:
    url: str
    username: str
    page_count: int
    posts: list[Post] = field(default_factory = list)