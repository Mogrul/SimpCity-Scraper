import logging

from .external_scraper import ExternalScraper
from src.simpcity.models.external_scraper_data import ExternalScraperData

class GoonBox(ExternalScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("external.goonbox"),
            *args,
            **kwargs
        )
    
    def scrape(self):
        super().scrape()
        
        for data in self._datas:            
            if "/album/" in data.url:
                self._handle_album(data)
            
            elif "/images" in data.url:
                self._handle_file(data)
    
    def _handle_album(self, data: ExternalScraperData):
        pass
    
    def _handle_file(self, data: ExternalScraperData):
        response = self.download(data)
        
        