from dataclasses import dataclass

@dataclass
class ExternalURL:
    url: str
    signed: str | None = None
    file_name: str | None = None