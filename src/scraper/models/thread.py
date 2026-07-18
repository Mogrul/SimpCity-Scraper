from dataclasses import dataclass, field

@dataclass
class Thread:
    id: int
    username: str
    tags: list[str] = field(default_factory = list)