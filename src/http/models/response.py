from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .request import HttpRequest

@dataclass
class HttpResponse:
    request: HttpRequest
    status_code: int
    soup: BeautifulSoup | None = None
    headers: dict[str, str] = field(default_factory = dict)