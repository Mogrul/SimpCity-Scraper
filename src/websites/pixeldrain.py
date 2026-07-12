import logging
from pathlib import Path

from bs4 import BeautifulSoup

from src.models import DownloadResult, ExternalURL
from .website import WebSite

class PixelDrain(WebSite):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("website.pixeldrain"),
            thread_name = "website.pixeldrain.thread",
            *args,
            **kwargs
        )
    
    def on_url_scrape(self, url: ExternalURL) -> list[DownloadResult] | None:
        super().on_url_scrape(url)
        
        if "/l/" in url.url:
            self.handle_album(url)
        
        if "/u/" in url.url:
            self.sign_and_download(url)
            
    def handle_album(self, url: ExternalURL) -> list[DownloadResult]:
        def get_album_id() -> str:
            return url.url.split("/")[-1]
        
        data = self.web.get(
            url = f"https://pixeldrain.com/api/list/{get_album_id()}",
            return_dict = True
        )
        
        if not isinstance(data, dict):
            return []
        
        results: list[DownloadResult] = []
        
        for file in data["files"]:
            if not isinstance(file, dict):
                continue
            
            file_id = file["id"]
            file_name = file["name"]
            
            external_url = ExternalURL(
                created_at = url.created_at,
                url = f"https://pixeldrain.com/u/{file_id}",
                domain_name = "pixeldrain",
                username = url.username,
                file_name = Path(file_name),
                tags = url.tags
            )
            
            result = self.sign_and_download(external_url)
            if not result:
                continue
            
            results.extend(result)
        
        return results
    
    def sign(self, url: ExternalURL) -> ExternalURL | None:
        def get_file_id() -> str:
            return url.url.split("/")[-1]

        def get_file_name() -> Path | None:
            headers = self.web.get(
                url = f"https://pixeldrain.com/api/file/{get_file_id()}",
                return_headers = True
            )
            
            if not isinstance(headers, dict):
                return None
            
            content_disposition = headers["Content-Disposition"]
            file_name = content_disposition.split("filename=")[-1].replace('"', "")
            
            return Path(file_name)
        
        if not url.file_name:
            file_name = get_file_name()
            
            if not file_name:
                return None
            
            url.file_name = file_name
        
        url.signed = f"https://pixeldrain.com/api/file/{get_file_id()}"
        
        return url
        