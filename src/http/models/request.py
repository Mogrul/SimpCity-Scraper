from dataclasses import dataclass

from ..enums import ResponseType

@dataclass
class HttpRequest:
    url: str
    referer: str | None = None
    origin: str | None = None