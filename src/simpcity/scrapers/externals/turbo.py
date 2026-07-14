import logging

from src.http.models import (
    HttpDownloadResponse,
    HttpRequest
)
from src.http.enums import ResponseType

from .external_scraper import ExternalScraper
from src.simpcity.models.external_scraper_data import ExternalScraperData
from .enums import Signing

class Turbo(ExternalScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("external.turbo"),
            thread_prefix = "turbo.thread",
            *args,
            **kwargs
        )
    
    def on_scrape(
            self,
            data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse] | None:
        super().on_scrape(data)
        
        if "/embed/" in data.url:
            return self._handle_embed(data)
    
    def _handle_embed(
            self,
            data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse] | None:
        id = data.url.split("/")[-1]
        api_url = Signing.TURBO + id
        
        response = self._client.get(HttpRequest(
            url = api_url,
            referer = data.url
        ), ResponseType.DICT)
        
        if not isinstance(response.data, dict):
            return None
        
        file_name = response.data.get("original_filename")
        url = response.data.get("url")
        
        if not file_name or not url:
            return None
        
        data.url = url
        data.file_name = file_name
        
        return (self.download(data),)