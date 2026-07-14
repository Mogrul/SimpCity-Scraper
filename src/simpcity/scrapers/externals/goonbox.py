import logging

from src.http.models import HttpDownloadResponse

from .external_scraper import ExternalScraper
from src.simpcity.models import ExternalScraperData

class GoonBox(ExternalScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("external.goonbox"),
            thread_prefix = "goonbox.thread",
            *args,
            **kwargs
        )
    
    def on_scrape(
            self,
            data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse, ...] | None:
        super().on_scrape(data)
        
        if "/album/" in data.url:
            self._logger.warning(f"GoonBox albums currently not supported!")
        
        elif "/images" in data.url:
            return self._handle_file(data)
    
    def _handle_file(
            self,
            data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse] | None:
        return (self.download(data),)
        
        