from enum import Enum

class ResponseType(Enum):
    DICT = "dict"
    SOUP = "soup"
    TEXT = "text"
    HEADERS = "headers"
    DOWNLOAD = "download"