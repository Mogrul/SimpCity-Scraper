from uuid import UUID
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid5, NAMESPACE_URL

from src.models import Post
from src.web import Web

BASE_PATH = Path("Downloads")

class WebSite:
    def __init__(
            self,
            username: str,
            post_map: dict[UUID, Post],
            posts: dict[UUID, Post],
            logger = logging.Logger,
            max_workers = 10
    ):
        self.username = username
        self.post_map = post_map
        self.posts = posts
        self.web = Web()
        self.max_workers = max_workers
        self.logger = logger
        
        self.link_map = self.create_link_map()
    
    def create_link_map(self) -> dict[str, datetime]:
        link_map: dict[str, datetime] = {}
        
        for post_id, urls in self.posts.items():
            post = self.post_map[post_id]
            
            for url in urls:
                link_map[url] = post.created_at
        
        return link_map
    
    def scrape(self):
        pass
    
    def get_file_path(self, url: str, created_at: datetime):
        parsed = urlparse(url)
        file_name = Path(parsed.path.replace("/", ""))
        file_id = str(uuid5(NAMESPACE_URL, parsed.geturl())).replace("-", "")[:-16]
        
        file_path = Path(
            BASE_PATH,
            self.username,
            str(created_at.year),
            f"{created_at.strftime('%B')}",
            f"[{created_at.year}-{created_at.month:02d}-{created_at.day:02d}] {file_id}{file_name.suffix}"
        )
        
        return file_path