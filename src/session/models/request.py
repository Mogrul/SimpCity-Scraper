from dataclasses import dataclass, field

from session.enums import RequestType, ResponseType


@dataclass
class Request:
    link: str
    request_type: RequestType
    response_type: ResponseType
    params: dict[str, str] = field(default_factory = dict)
    headers: dict[str, str] = field(default_factory = dict)
    payload: dict[str, str] = field(default_factory = dict)