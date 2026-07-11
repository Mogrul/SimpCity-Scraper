from uuid import UUID
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid5, NAMESPACE_URL

from src.models import Post
from src.web import Web

class WebSite:
    def __init__(
            self,
            username: str,
            post_map: dict[UUID, Post],
            posts: dict[UUID, list[str]],
            base_path: Path,
            chunk_size: int,
            timeout: int,
            logger: logging.Logger | None = None,
            max_workers = 10,
    ):
        self.username = username
        self.post_map = post_map
        self.posts = posts
        self.web = Web(
            chunk_size = chunk_size,
            timeout = timeout
        )
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__) if not logger else logger
        self.base_path = base_path
        
        self.url_map = self.create_url_map()
    
    def create_url_map(self) -> dict[str, datetime]:
        url_map: dict[str, datetime] = {}
        
        for post_id, urls in self.posts.items():
            post = self.post_map[post_id]
            
            for url in urls:
                url_map[url] = post.created_at
        
        return url_map
    
    def scrape(self):
        pass
    
    def get_file_path(self, url: str, created_at: datetime):
        def get_file_name() -> Path:
            file_name = parsed.path.replace("/", "")
            
            if "?" in file_name:
                file_name = file_name.split("?")[0]
            
            return Path(file_name)
        
        parsed = urlparse(url)
        file_name = get_file_name()
        file_id = str(uuid5(NAMESPACE_URL, parsed.geturl())).replace("-", "")[:-16]
        
        file_path = Path(
            self.base_path,
            self.username,
            str(created_at.year),
            f"{created_at.strftime('%B')}",
            f"[{created_at.year}-{created_at.month:02d}-{created_at.day:02d}] {file_id}{file_name.suffix}"
        )
        
        return file_path

    def handle_url(self, url: str, created_at: datetime) -> list[dict] | None:
        pass