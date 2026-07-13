from dataclasses import dataclass
from pathlib import Path

from .download_request import HttpDownloadRequest

@dataclass
class HttpDownloadResponse:
    request: HttpDownloadRequest
    success: bool = True
    is_duplicate: bool = False
    status_code: int | None = None
    size: int | None = None
    time_taken: float | None = None