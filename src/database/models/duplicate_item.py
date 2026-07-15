from dataclasses import dataclass
from pathlib import Path

@dataclass
class DuplicateItem:
    kept_path: Path
    deleted_path: Path
    kept_size: int # bytes
    deleted_size: int # bytes
    similarity: float