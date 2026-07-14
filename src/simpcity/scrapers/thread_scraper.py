from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from bs4 import BeautifulSoup

from src.http.client import HTTPClient
from src.http.models import HTTPRequest
from src.http.enums import ResponseType, RequestType
from src.shared import Config
from ..models import Thread, Post, ExternalURL
from .page_scraper import PageScraper

class ThreadScraper:
    def __init__(self):
        self._logger = logging.getLogger("simpcity.thread")
        self._http_client = HTTPClient()
        self._config = Config()
    
    def scrape(self, url: str) -> tuple[Thread, list[Post]] | None:
        # Remove paged url if present
        if "/page-" in url:
            url = url.split("/page-")[0]
        
        elif url.endswith("/"):
            url = url[:-1]
        
        # Get first page
        request = HTTPRequest(url, RequestType.GET, ResponseType.SOUP)
        response = self._http_client.send(request)
        
        if not isinstance(response.data, BeautifulSoup):
            return
        
        soup = response.data
        max_page_num = self._get_max_page_num(soup)
        
        # Create a thread object to later add posts to
        username = self._get_username(url)
        id = self._get_id(url)
        tags = self._get_tags(soup)
        
        if not username:
            self._logger.error(f"Failed to extract username from {url}")
            return
        
        if not id:
            self._logger.error(f"Failed to extract thread ID from {url}")
            return
        
        thread = Thread(
            url = url,
            id = id,
            page_count = max_page_num,
            username = username,
            tags = tags
        )

        # get posts from first page
        posts = []
        scraper = PageScraper()
        
        posts.extend(scraper.scrape(response.data, url))
        
        # Recurse through pages using a thread pool
        if max_page_num != 1:
            with ThreadPoolExecutor(self._config.workers, "simpcity.thread.thread") as executor:
                futures = [
                    executor.submit(self._scrape_page, url, page_num)
                    for page_num in range(2, max_page_num + 1)
                ]
                
                for future in as_completed(futures):
                    try:
                        page_posts = future.result()
                    
                    except Exception as e:
                        self._logger.error(f"Exception getting page posts: {e}")
                        continue
                    
                    if not isinstance(page_posts, list):
                        continue
                    
                    posts.extend(page_posts)
                
        # Return thread object and posts
        return (thread, posts)

    def _scrape_page(self, url: str, page_num: int) -> list[Post]:
        scraper = PageScraper()
        paged_url = f"{url}/page-{page_num}"
        request = HTTPRequest(paged_url, RequestType.GET, ResponseType.SOUP)
        response = self._http_client.send(request)
        
        if not isinstance(response.data, BeautifulSoup):
            return []
                
        return scraper.scrape(response.data, url)
    
    def _get_max_page_num(self, soup: BeautifulSoup) -> int:
        page_navs = soup.find_all("li", class_ = "pageNav-page")
        if not page_navs:
            return 1
        
        last_lav = page_navs[-1]
        
        try:
            return int(last_lav.get_text())

        except KeyError:
            return 1
    
    def _get_username(self, url: str) -> str:
        username = url.split("/")[-1].split(".")[0]
        items = username.split("-")
        
        return " ".join(item.title() for item in items[:2])
    
    def _get_id(self, url: str) -> int | None:
        id_str = url.split(".")[-1]
        
        try:
            return int(id_str)
        
        except KeyError:
            return

    def _get_tags(self, soup: BeautifulSoup) -> list[str]:
        tags = []
        
        labels = soup.find_all("span", class_ = "label")
        for label in labels:
            text = label.get_text(strip = True)
            
            if not isinstance(text, str):
                continue
            
            tags.append(text)
        
        # Strip spaces in tags
        return [tag.replace(" ", "") for tag in tags]