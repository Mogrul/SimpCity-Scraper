from enum import Enum

class ResponseType(str, Enum):
    SOUP = "soup"
    DICT = "dict"
    TEXT = "text"