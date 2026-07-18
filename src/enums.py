from enum import Enum


class ResponseType(Enum):
    SOUP = "soup"
    DICT = "dict"

class RequestType(Enum):
    POST = "post"
    GET = "get"

class StatusCode(Enum):
    SUCCESS = 200
    FAILED = 400
    TIMEOUT = 504
    FAILED_PATH = 505
    FAILED_EXISTS = 506