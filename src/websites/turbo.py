import logging
from pathlib import Path

from src.models import ExternalURL, DownloadResult
from .website import WebSite

class Turbo(WebSite):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("website.turbo"),
            thread_name = "website.turbo.thread",
            *args,
            **kwargs
        )
    
    def on_url_scrape(self, url: ExternalURL) -> list[DownloadResult] | None:
        super().on_url_scrape(url)
        return self.sign_and_download(url)
        
    def sign(self, url: ExternalURL) -> ExternalURL | None:
        def get_embed_id() -> str:
            return url.url.split("/")[-1]
        
        api_url = "https://turbo.cr/api/sign?v=" + get_embed_id()
        data = self.web.get(
            api_url,
            referer = url.url,
            return_dict = True
        )
        
        if isinstance(data, dict):
            if data.get("success", False):
                url.signed = data["url"]
                url.file_name = Path(data["filename"])
        
        return url