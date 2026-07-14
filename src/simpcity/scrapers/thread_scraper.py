import logging

from bs4 import BeautifulSoup

from .page_scraper import PageScraper
from ..models import Thread
from src.http.enums import ResponseType
from src.http.http_client import HttpClient

from src.http.models import (
    HttpRequest,
    HttpResponse
)

class ThreadScraper:
    def __init__(self):
        self._logger = logging.getLogger("scraper.thread")
        self._client = HttpClient()
    
    @classmethod
    def scrape(cls, url: str) -> Thread | None:
        scraper = cls()

        response = scraper._get_page(url, 1)
        if (
            not response.status_code == 200
            or not isinstance(response.data, BeautifulSoup)
        ):
            scraper._logger.error(f"Failed to get soup from {url}")
            return
        
        username = scraper._get_username(response.data)
        tags = scraper._get_tags(response.data)
        
        if not username:
            scraper._logger.error(f"Failed to retreive username from {url}")
            return
        
        thread = Thread(
            username = username,
            url = url,
            tags = tags
        )
        
        max_page_num = scraper._get_max_page_num(response.data)
        for page_num in range(1, max_page_num + 1):
            if page_num != 1:
                response = scraper._get_page(url, page_num)
                if (
                    not response.status_code == 200
                    or not response.data
                ):
                    scraper._logger.error(f"Failed to get soup from page: {response.request.url}")
                    return
            
            page = PageScraper.scrape(response)
            
            if not page:
                scraper._logger.error(f"Failed to get page from: {response.request.url}")
                return
            
            thread.pages.append(page)
        
        return thread
    
    def _get_page(self, url: str, page_num: int) -> HttpResponse:
        url = url + f"/page-{page_num}"
        
        return self._client.get(HttpRequest(
            url = url,
            referer = "https://simpcity.cr"
        ), ResponseType.SOUP)
    
    def _get_max_page_num(self, soup: BeautifulSoup) -> int:
        page_nav_main = soup.find("ul", class_ = "pageNav-main")
        
        if not page_nav_main: return 1
        
        page_navs = page_nav_main.find_all("li", class_ = "pageNav-page")
        last_page_nav = page_navs[-1]
        
        try:
            return int(last_page_nav.get_text())

        except KeyError:
            return 0
    
    def _get_username(self, soup: BeautifulSoup) -> str | None:
        h1 = soup.find("h1", class_ = "p-title-value")
        
        if not h1:
            return None
        
        return "".join(h1.find_all(string = True, recursive = False)).strip()
    
    def _get_tags(self, soup: BeautifulSoup) -> list[str]:
        h1 = soup.find("h1", class_ = "p-title-value")
        
        if not h1:
            return []
        
        return [span.get_text(strip = True) for span in h1.select("span.label")]