from dataclasses import dataclass

from enums import StatusCode
from .download_request import DownloadRequest


@dataclass
class DownloadResponse:
    status_code: StatusCode
    request: DownloadRequest | None = None
    time_taken: float | None = None
    file_size: int | None = None