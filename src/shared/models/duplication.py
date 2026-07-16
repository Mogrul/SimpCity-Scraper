from dataclasses import dataclass

@dataclass
class Duplication:
    videos: bool
    images: bool
    samples: int
    threshold: float