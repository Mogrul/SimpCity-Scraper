from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NetworkConfig:
    timeout: int
    chunk_size: int
    cookies: Path
    headers: dict = field(default_factory = dict)