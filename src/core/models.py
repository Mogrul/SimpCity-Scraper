from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Author:
    username: str
    joined_at: datetime
    posts_created: int
    reactions_received: int

@dataclass
class Post:
    author: Author
    posted_at: datetime
    links: list[str] = field(default_factory = list)