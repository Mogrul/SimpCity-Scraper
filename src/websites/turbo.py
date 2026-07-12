import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from src.models import ExternalURL, DownloadResult
from .website import WebSite


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
    
    def on_url_scrape(self, url: ExternalURL) -> list[DownloadResult] | None:
        super().on_url_scrape(url)
        
        signed = self.sign(url.url)
        
        if not signed:
            return []
        
        url.url = signed
        file_path = self.get_file_path(url)
        downloaded = self.web.download(url, file_path)
        
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