from dataclasses import dataclass, field

@dataclass
class Thread:
    id: int
    username: str
    max_page_num: int
    tags: list[str] = field(default_factory = list)