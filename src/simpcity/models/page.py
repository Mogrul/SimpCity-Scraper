from dataclasses import dataclass, field

from .post import Post

@dataclass
class Page:
    url: str
    page_num: int
    posts: list[Post] = field(default_factory = list)