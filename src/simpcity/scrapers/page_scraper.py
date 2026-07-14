import logging

from bs4 import BeautifulSoup

from ..models import Post
from .post_scraper import PostScraper

class PageScraper:
    def __init__(self):
        self._logger = logging.getLogger("simpcity.page")
    
    def scrape(self, page: BeautifulSoup, url: str) -> list[Post]:
        posts: list[Post] = []
        post_divs = page.find_all("div", class_ = "message-cell--main")
        post_divs = post_divs[:-1] # Last = message box
                
        # Recursve through post objects and extend posts
        scraper = PostScraper()
        for post_div in post_divs:
            post = scraper.scrape(post_div, url)
            
            if not post: continue
            
            posts.append(post)
        
        return posts