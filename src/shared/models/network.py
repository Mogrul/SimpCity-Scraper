from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Network:
    workers: int
    timeout: int
    chunk_size: int
    cookie_path: Path
    headers: dict[str, str] = field(default_factory = dict)