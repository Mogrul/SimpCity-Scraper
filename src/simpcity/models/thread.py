from dataclasses import dataclass, field

from .page import Page

@dataclass
class Thread:
    username: str
    url: str
    tags: list[str] = field(default_factory = list)
    pages: list[Page] = field(default_factory = list)