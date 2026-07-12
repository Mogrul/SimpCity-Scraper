import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid5, NAMESPACE_URL
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.models import ExternalURL, DownloadResult
from src.web import Web

class WebSite:
    def __init__(
            self,
            urls: list[ExternalURL],
            base_path: Path,
            chunk_size: int,
            timeout: int,
            logger: logging.Logger | None = None,
            max_workers = 10,
            thread_name = "WebSite"
    ):
        self.max_workers = max_workers
        self.base_path = base_path
        self.urls = urls
        self.thread_name = thread_name
        self.logger = (
            logging.getLogger(__name__)
            if not logger else logger
        )

        self.web = Web(
            chunk_size = chunk_size,
            timeout = timeout
        )
            
    def scrape(self): 
        with ThreadPoolExecutor(
                max_workers = self.max_workers,
                thread_name_prefix = self.thread_name
        ) as executor:
            future_to_url = {
                executor.submit(self.on_url_scrape, url): url
                for url in self.urls
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]

                try:
                    results = future.result()
                except Exception as e:
                    self.logger.error(f"Error downloading {url}: {e}")
                
                if not results: continue
                
                for result in results:
                    if not isinstance(result, DownloadResult):
                        continue
                    
                    self.logger.info(f"Downloaded {result.url.url} -> {result.path}")
            
    def on_url_scrape(self, url: ExternalURL) -> list[dict] | None:
        pass
    
    def get_file_path(self, url: ExternalURL):
        def get_file_name() -> Path:
            file_name = parsed.path.replace("/", "")
            
            if "?" in file_name:
                file_name = file_name.split("?")[0]
            
            return Path(file_name)
        
        parsed = urlparse(url.url)
        file_name = get_file_name()
        file_id = str(
            uuid5(NAMESPACE_URL, parsed.geturl())
        ).replace("-", "")[:-16]
        
        tag_path = (url.tags[0],) if url.tags else ()

        file_path = Path(
            self.base_path,
            *tag_path,
            url.username,
            str(url.created_at.year),
            f"{url.created_at.strftime('%B')}",
            f"[{url.created_at.year}-{url.created_at.month:02d}-{url.created_at.day:02d}] {file_id}{file_name.suffix}",
        )
        
        return file_path

    def handle_url(self, url: str, created_at: datetime) -> list[dict] | None:
        pass