import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from .website import WebSite
from src.util import format_bytes

class Turbo(WebSite):
    def __init__(self, *args, **kwargs):
        logger = kwargs.pop("logger")
        if not logger:
            logger = logging.getLogger("website.turbo")
        
        super().__init__(
            logger = logger,
            *args,
            **kwargs
        )
    
    def scrape(self):
        with ThreadPoolExecutor(
                max_workers = self.max_workers,
                thread_name_prefix = "website.turbo.thread"
        ) as executor:
            futures = [
                executor.submit(self.handle_url, url, created_at)
                for url, created_at in self.url_map.items()
            ]
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                
                except Exception as e:
                    self.logger.exception(f"Error handling url: {e}")
                    continue
                
                if not result: continue
                
                for data in result:
                    self.logger.info(
                        f"Downloaded {format_bytes(data['size'])} -> {data['destination']}"
                    )
        
        for url, created_at in self.url_map.items():
            signed = self.sign(url)
            
            if not signed: continue
            
            file_path = self.get_file_path(signed, created_at)
            self.web.download(
                signed,
                destination = file_path,
                return_dict = True
            )
    
    def handle_url(self, url: str, created_at: datetime) -> list[dict]:
        signed = self.sign(url)
        
        if not signed:
            return []
        
        file_path = self.get_file_path(signed, created_at)
        downloaded = self.web.download(
            signed,
            destination = file_path,
            return_dict = True
        )
        
        if not downloaded:
            return []
        
        if not isinstance(downloaded, dict):
            return []
        
        return [downloaded]
        
    
    def sign(self, url: str) -> str | None:
        def get_embed_id() -> str:
            return url.split("/")[-1]
        
        api_url = "https://turbo.cr/api/sign?v=" + get_embed_id()
        data = self.web.get(
            api_url,
            referer = url,
            return_dict = True
        )
        
        if isinstance(data, dict):
            if data.get("success", False):
                return data["url"]
        
        return None