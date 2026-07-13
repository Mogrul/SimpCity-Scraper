from dataclasses import dataclass

@dataclass
class HttpRequest:
    url: str
    as_soup: bool = True
    referer: str | None = None
    origin: str | None = None