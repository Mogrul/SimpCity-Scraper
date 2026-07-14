from dataclasses import dataclass

from ..enums import ResponseType

@dataclass
class HttpGetRequest:
    url: str
    referer: str | None = None
    origin: str | None = None
    host: str | None = None