import logging

from .scrapers.thread_scraper import ThreadScraper

class SimpCity:
    def __init__(self):
        self._logger = logging.getLogger("simpcity")
    
    def scrape(self, url: str):
        if url.endswith("/"):
            url = url[:-1]
        
        thread = ThreadScraper.scrape(url)