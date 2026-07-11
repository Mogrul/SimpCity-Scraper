from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from datetime import datetime
import json
from urllib.parse import urlparse

from .website import WebSite
from src.util import format_bytes

class GoonBox(WebSite):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("website.goonbox"),
            *args,
            **kwargs
        )
    
    def scrape(self):
        with ThreadPoolExecutor(
                max_workers = self.max_workers,
                thread_name_prefix = "website.goonbox.thread"
        ) as executor:
            futures = [
                executor.submit(self.handle_link, link, created_at)
                for link, created_at in self.link_map.items()
            ]
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                
                except Exception as e:
                    self.logger.exception(f"Error handling link: {e}")
                    continue
    
                if not result: continue
                
                for data in result:
                    self.logger.info(
                        f"Downloaded {format_bytes(data['size'])} -> {data['destination']}"
                    )
    
    def handle_link(self, url: str, created_at: datetime):
        if "/a/" in url:
            # Album
            return self.handle_album(url, created_at)
        
        return self.handle_image(url, created_at)
        
    def handle_album(self, url: str, created_at: datetime) -> list[dict]:
        def get_album_id() -> str:
            id =  url.split("/a/")[1].split("/")[0]
            if "." in id:
                return id.split(".")[-1]
            else:
                return id
        
        def download_page(image: dict) -> dict | None:
            img_url = image.get("original_url")
            if not img_url: return
            
            download = self.handle_image(img_url, created_at)
            if not download:
                return
            
            return download
        
        parsed = urlparse(url)
        album_id = get_album_id()
        api_url = urlparse("https://" + parsed.netloc + f"/api/albums/{album_id}")
        
        data = self.web.get(api_url, referer = parsed, return_dict = True)
        
        last_page = data["pagination"]["last_page"]
        
        for page_num in range(1, last_page + 1):
            if page_num != 1:
                paged_url = urlparse(api_url.geturl() + f"/images?page={page_num}")
                data = self.web.get(paged_url, referer = parsed, return_dict = True)
            
            images: list[dict] = data["images"]
            
            with ThreadPoolExecutor(
                    self.max_workers,
                    thread_name_prefix = "website.goonbox.thread"
            ) as executor:
                futures = [
                    executor.submit(download_page, image)
                    for image in images
                ]
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    
                    except Exception as e:
                        self.logger.exception(f"Error downloading page: {e}")
                        continue
                    
                    if not result: continue
                    for data in result:
                        self.logger.info(
                            f"Downloaded {format_bytes(data['size'])} -> {data['destination']}"
                        )    
    
    def handle_image(self, url: str, created_at: datetime) -> list[dict]:
        file_path = self.get_file_path(url, created_at)
        downloaded = self.web.download(urlparse(url), destination = file_path, return_dict = True)
        
        if not downloaded:
            return []
        
        return [downloaded]
    