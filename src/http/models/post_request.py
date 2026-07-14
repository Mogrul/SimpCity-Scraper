from dataclasses import dataclass

@dataclass
class HttpPostRequest:
    url: str
    payload: dict
    referer: str | None = None
    origin: str | None = None
    host: str | None = None