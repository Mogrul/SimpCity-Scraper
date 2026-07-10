from datetime import datetime, timedelta
import logging

from bs4 import BeautifulSoup, Tag
import tldextract

from .session import Session
from .models import Author, Post
from .websites import WEBSITES
from .util import get_username_from_url

class Core:
    def __init__(self):
        self.session = Session()
        self.logger = logging.getLogger("core")
    
    def scrape(self, url: str):
        self.logger.info(f"Scraping: {url}")
        
        username = get_username_from_url(url)
        page = self.session.get(url)
        max_page_count = self.get_page_max_count(page)
        
        for page_num in range(1, max_page_count + 1):
            url_with_pagenum = self.get_page_with_number(url, page_num)
            page = self.session.get(url_with_pagenum)
            
            posts = self.get_posts_in_page(page)
            self.scrape_posts(posts, username)
    
    def scrape_posts(self, posts: list[Post], username: str):
        for post in posts:            
            for link in post.links:
                domain = tldextract.extract(link).domain
                
                if "https" not in link:
                    continue
                
                if domain not in WEBSITES:
                    self.logger.warning(f"Domain not supported: {domain}")
                    continue
                
                website = WEBSITES.get(domain)
                website = website(link, post, username)
                website.download()
    
    def get_page_max_count(self, page: BeautifulSoup) -> int:
        page_nav_main = page.find("ul", class_ = "pageNav-main")
        if not page_nav_main:
            return 1

        page_navs = page_nav_main.find_all("li", class_ = "pageNav-page")
        last_nav = page_navs[-1]
        a = last_nav.find("a")
        
        self.logger.info(f"Found {a.get_text()}")
        
        try:
            return int(a.get_text())
        
        except TypeError:
            return 1
    
    def get_page_with_number(self, url: str, page_num: int):
        if url.endswith("/"):
            url_with_pagenum = url + f"page-{page_num}"
        
        else:
            url_with_pagenum = url + f"/page-{page_num}"
        
        return url_with_pagenum
    
    def get_posts_in_page(self, page: BeautifulSoup):
        message_inners = page.find_all("div", class_ = "message-inner")
        message_inners = message_inners[:-1] # Last item = message box
        
        posts: list[Post] = []
        
        for message in message_inners:
            author_cell = message.find("div", class_ = "message-cell--user")
            main_cell = message.find("div", class_ = "message-cell--main")
            
            author = self.get_author_in_post(author_cell)
            post = self.get_post_in_page(main_cell, author)
            
            posts.append(post)

        return posts
                
    def get_author_in_post(self, author_cell: Tag) -> Author:
        username = author_cell.find("h4", class_ = "message-name").get_text(strip = True)
        joined_date_str = author_cell.find("dd").get_text(strip = True)
        joined_at = datetime.strptime(joined_date_str, "%b %d, %Y")
        
        pairs = author_cell.find_all("dd")
        joined_at: datetime = None
        posts_created: int = None
        reactions_received: int = None
        
        for x in range(len(pairs)):
            text = pairs[x].get_text(strip = True).replace(",", "")
            
            match x:
                case 0:
                    joined_at = datetime.strptime(text, "%b %d %Y")
                
                case 1:
                    posts_created = int(text)
                
                case 2:
                    reactions_received = int(text)
        
        author = Author(
            username = username,
            joined_at = joined_at,
            posts_created = posts_created,
            reactions_received = reactions_received
        )
        
        return author
    
    def get_post_in_page(self, main_cell: Tag, author: Author):
        time_str = main_cell.find("time").get_text().replace(",", "")
        try:
            posted_at = datetime.strptime(time_str, "%b %d %Y")
        
        except ValueError:
            now = datetime.now()
            
            if time_str.startswith("Today at "):
                time_part = time_str.removeprefix("Today at ")
                t = datetime.strptime(time_part, "%I:%M %p").time()
                posted_at = datetime.combine(now.date(), t)

            elif time_str.startswith("Yesterday at "):
                time_part = time_str.removeprefix("Yesterday at ")
                t = datetime.strptime(time_part, "%I:%M %p").time()
                posted_at = datetime.combine(now.date() - timedelta(days=1), t)

            else:
                day_name, time_part = time_str.split(" at ")
                t = datetime.strptime(time_part, "%I:%M %p").time()

                target_weekday = datetime.strptime(day_name, "%A").weekday()
                days_ago = (now.weekday() - target_weekday) % 7

                posted_at = datetime.combine(
                    now.date() - timedelta(days=days_ago),
                    t
                )
        
        bbwrapper = main_cell.find("div", class_ = "bbWrapper")
        external_links = bbwrapper.find_all("a", class_ = "link--external")
        
        links: list[str] = []
        for external_link in external_links:
            text = external_link.get_text(strip = True)
            
            if not text:
                continue
            
            links.append(text)
        
        return Post(
            author = author,
            posted_at = posted_at,
            links = links
        )