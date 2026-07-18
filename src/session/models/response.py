from dataclasses import dataclass

from bs4 import BeautifulSoup

from .request import Request
from session.enums import StatusCode


@dataclass
class Response:
    request: Request
    status_code: StatusCode
    data: dict | BeautifulSoup | str | None = None