from dataclasses import dataclass


@dataclass
class Link:
    post_id: int
    link: str
    domain: str
    signed: str | None = None
    filename: str | None = None