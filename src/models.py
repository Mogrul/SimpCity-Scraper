from dataclasses import dataclass
from pathlib import Path

@dataclass
class DuplicationResult:
    deleted_count: int
    bytes_saved: int

    def __iadd__(self, other: "DuplicationResult") -> DuplicationResult:
        self.bytes_saved += other.bytes_saved
        self.deleted_count += other.deleted_count

        return self

@dataclass
class MarkedDelete:
    file1: Path
    file2: Path