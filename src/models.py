from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from enums import RequestType, ResponseType, StatusCode


@dataclass
class Request:
    link: str
    request_type: RequestType
    response_type: ResponseType
    params: dict[str, str] = field(default_factory = dict)

@dataclass
class Response:
    request: Request
    status_code: StatusCode
    data: dict | BeautifulSoup | str | None = None

@dataclass
class DownloadRequest:
    link: str
    destination: Path
    headers: dict[str, str] = field(default_factory = dict)
    params: dict[str, str] = field(default_factory = dict)

@dataclass
class DownloadResponse:
    status_code: StatusCode
    request: DownloadRequest | None = None
    time_taken: float | None = None
    file_size: int | None = None

@dataclass
class DownloadConfig:
    location: Path

@dataclass
class NetworkConfig:
    timeout: int
    chunk_size: int
    cookies: Path
    headers: dict = field(default_factory = dict)

@dataclass
class DuplicationConfig:
    images: bool
    videos: bool
    ffmpeg_path: Path
    ffprobe_path: Path
    threshold: float
    samples: int

@dataclass
class DatabaseConfig:
    enabled: bool
    location: Path

@dataclass
class Thread:
    id: int
    username: str
    tags: list[str] = field(default_factory = list)

@dataclass
class Post:
    id: int
    date: datetime

@dataclass
class Link:
    post_id: int
    link: str
    domain: str
    signed: str | None = None
    filename: str | None = None

@dataclass
class DomainResult:
    downloaded: int
    duplicate: int
    failed: int
    completed_links: dict[Path, str] = field(default_factory = dict)

    def __iadd__(self, other: "DomainResult") -> DomainResult:
        self.downloaded += other.downloaded
        self.duplicate += other.duplicate
        self.failed += other.failed

        return self

@dataclass
class MarkedDelete:
    file1: Path
    file2: Path