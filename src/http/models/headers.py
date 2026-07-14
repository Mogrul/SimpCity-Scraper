from dataclasses import dataclass

@dataclass
class HTTPHeaders:
    user_egent: str | None = None
    accept: str | None = None
    accept_encoding: str | None = None
    referer: str | None = None