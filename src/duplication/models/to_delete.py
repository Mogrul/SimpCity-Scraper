from dataclasses import dataclass

from pathlib import Path

@dataclass
class ToDelete:
    file_1: Path
    file_2: Path
    similarity: float