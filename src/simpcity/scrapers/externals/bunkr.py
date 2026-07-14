import logging

from src.simpcity.models import ExternalScraperData
from src.http.models import (
    HttpDownloadResponse,
    HttpRequest
)
from src.http.enums import ResponseType
from .external_scraper import ExternalScraper

class Bunkr(ExternalScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("external.bunkr"),
            thread_prefix = "bunkr.thread",
            *args,
            **kwargs
        )
    
    def on_scrape(
            self,
            data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse] | None:
        super().on_scrape(data)
        
        if "/a/" in data.url:
            return self._handle_album(data)
    
    def _handle_album(
            self,
            data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse] | None:
        super()._handle_album(data)
        
        return
    
    def _handle_file(
            self,
            data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse] | None:
        super()._handle_file(data)
        
        return 