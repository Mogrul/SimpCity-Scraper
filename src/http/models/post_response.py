from dataclasses import dataclass

from .post_request import HttpPostRequest

@dataclass
class HttpPostResponse:
    request: HttpPostRequest
    status_code: int
    headers: dict
    data: dict | None = None