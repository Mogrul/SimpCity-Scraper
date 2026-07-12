import logging
from pathlib import Path

from src.models import ExternalURL, DownloadResult
from .website import WebSite

class CyberDrop(WebSite):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("website.cyberdrop"),
            thread_name = "website.cyberdrop.thread",
            *args,
            **kwargs
        )
    
    def on_url_scrape(self, url: ExternalURL) -> list[DownloadResult] | None:
        super().on_url_scrape(url)
        return self.sign_and_download(url)
    
    def sign(self, url: ExternalURL) -> ExternalURL | None:
        def get_file_id() -> str:
            return url.url.split("/")[-1]
        
        data = self.web.get(
            f"https://api.cyberdrop.cr/api/file/info/{get_file_id()}",
            return_dict = True
        )
                
        if not isinstance(data, dict):
            return
        
        url.file_name = Path(data["name"])
        
        auth_data = self.web.get(
            data["auth_url"],
            origin = "https://cyberdrop.cr",
            referer = "https://cyberdrop.cr/",
            return_dict = True
        )
        
        if not isinstance(auth_data, dict):
            return
                
        url.signed = auth_data["url"]
        
        return url