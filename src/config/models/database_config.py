from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatabaseConfig:
    enabled: bool
    location: Path