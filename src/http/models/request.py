from dataclasses import dataclass

from ..enums import RequestType, ResponseType

@dataclass
class HTTPRequest:
    url: str
    request_type: RequestType
    response_type: ResponseType
    payload: dict | None = None