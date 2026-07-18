from enum import Enum

class StatusCode(Enum):
    SUCCESS = 200
    FAILED = 400
    TIMEOUT = 504
    FAILED_PATH = 505
    FAILED_EXISTS = 506