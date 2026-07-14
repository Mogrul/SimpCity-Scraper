import logging

from bs4 import BeautifulSoup, Tag

from ..models import Page
from .post_scraper import PostScraper
from src.http.models import HttpGetResponse

class PageScraper:
    def __init__(self):
        self._logger = logging.getLogger("scraper.page")
    
    @classmethod
    def scrape(cls, response: HttpGetResponse) -> Page | None:
        if (
            response.status_code != 200
            or not isinstance(response.data, BeautifulSoup)
        ):
            return
        
        scraper = cls()
        url = response.request.url
        
        page = Page(
            url = url,
            page_num = scraper._get_page_num(url)
        )
        
        post_tags = scraper._get_post_blocks(response.data)  
        if not post_tags:
            scraper._logger.error(f"Failed to get post tags in {url}")
            return
              
        for post_tag in post_tags:
            post = PostScraper.scrape(url, post_tag)
            
            if not post:
                scraper._logger.error(f"Failed to scrape post tag in {url}")
                return
            
            page.posts.append(post)
        
        scraper._logger.info(f"Found {len(page.posts)} posts in {url}")
        
        return page
    
    def _get_page_num(self, url: str) -> int:
        page_str = url.split("/")[-1].split("page-")[-1]
        
        try:
            return int(page_str)

        except KeyError:
            return 0
    
    def _get_post_blocks(self, soup: BeautifulSoup) -> list[Tag] | None:
        blocks = soup.find_all("article", class_ = "message--post")
        
        if not blocks: return None
        return blocks
        