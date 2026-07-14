from dataclasses import dataclass, field

@dataclass
class Thread:
    url: str
    username: str
    
    id: int
    page_count: int
    
    tags: list[str] = field(default_factory = list)