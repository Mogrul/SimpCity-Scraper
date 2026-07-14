from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .get_request import HttpGetRequest

@dataclass
class HttpGetResponse:
    request: HttpGetRequest
    status_code: int
    data: BeautifulSoup | dict | str | None = None
    headers: dict[str, str] = field(default_factory = dict)