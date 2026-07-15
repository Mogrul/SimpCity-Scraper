from dataclasses import dataclass

from bs4 import BeautifulSoup

from .request import HTTPRequest

@dataclass
class HTTPResponse:
    request: HTTPRequest
    status_code: int
    data: BeautifulSoup | str | dict | None = None
    headers: dict | None = None