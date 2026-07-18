from dataclasses import dataclass
from pathlib import Path


@dataclass
class MarkedDelete:
    file1: Path
    file2: Path