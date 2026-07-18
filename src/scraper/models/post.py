from dataclasses import dataclass
from datetime import datetime


@dataclass
class Post:
    id: int
    date: datetime