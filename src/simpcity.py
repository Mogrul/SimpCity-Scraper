from urllib.parse import urlparse, ParseResult
import logging
from datetime import datetime
from collections import defaultdict
from uuid import UUID
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from .support import SUPPORTED_SITES
from .websites import WEBSITES
from .web import Web
from .models import Post, Thread
from .util import is_valid_url, to_dict
from .duplication import Duplication

class SimpCity:
    def __init__(
            self,
            urls: list[str]
    ):
        self.logger = logging.getLogger("simpcity")
        self.notified_unsupported: set[str] = set()
        self.urls: list[ParseResult] = self.clean_urls(urls)
        self.web = Web()
        self.duplication = Duplication()
        
        self.post_map: dict[UUID, Post] = {}
        self.domain_map: dict[str, dict[UUID, list[str]]] = {}
            
    def clean_urls(self, urls: list[str]) -> list[str]:
        scrapable_urls = []
        
        for url in urls:
            parsed = urlparse(url)

            if (
                    not parsed.scheme in ("http", "https")
                    and not parsed.netloc
            ):
                self.logger.warning(f"Skipping invalid site: {url}")
                continue
            
            url = parsed.geturl()
            
            if (
                    parsed.netloc not in SUPPORTED_SITES
                    and parsed.netloc not in self.notified_unsupported
            ):    
                self.logger.warning(f"Unsupported site: {parsed.netloc}")
                self.notified_unsupported.add(parsed.netloc)
                continue
            
            scrapable_urls.append(parsed)

        return scrapable_urls
    
    def scrape(self):
        for url in self.urls:
            username = self.get_username(url).capitalize()
            soup = self.web.get(url)
            
            if not soup:
                continue
            
            max_page_count = self.get_max_page_count(soup)
            
            thread = Thread(
                url = url.geturl(),
                username = username,
                page_count = max_page_count
            )
            
            for page_num in range(1, max_page_count + 1):
                page_url = self.get_page_url(url, page_num)
                
                if page_num != 1:
                    soup = self.web.get(page_url, referer = url)
                
                posts = self.get_posts_in_page(soup)
                thread.posts.extend(posts)
            
            self.domain_map = self.sort_posts_by_domain(thread)
            self.scrape_domains(username)
            
            # Clear post map on completion
            self.post_map.clear()
            self.domain_map.clear()
            
            # Check for duplicates
            self.duplication.check_duplicate_images(Path("Downloads", username))

    def scrape_domains(self, username: str):
        for domain in self.domain_map.keys():
            if domain not in SUPPORTED_SITES:
                continue
            
            site = WEBSITES.get(domain)
            
            if not site:
                self.logger.error(f"Failed to get site from domain {domain}")
                continue
            
            site = site(
                username = username,
                post_map = self.post_map,
                posts = self.domain_map[domain]
            )
            site.scrape()

    def get_username(self, url: ParseResult) -> str:
        path = url.path
        thread_name = path.split("/")[-1]
        username = thread_name.split("-")[0]
        
        return username
    
    def get_page_url(self, url: ParseResult, page_num: int) -> ParseResult:
        return urlparse(url.geturl() + f"/page-{page_num}")
    
    def get_max_page_count(self, soup: BeautifulSoup) -> int:
        page_navs_main = soup.find("ul", class_ = "pageNav-main")
        
        if not page_navs_main:
            return 1
        
        page_navs = page_navs_main.find_all("li", class_ = "pageNav-page")
        last_page_nav = page_navs[-1]
        content = last_page_nav.get_text()
        
        try:
            return int(content)
        
        except KeyError:
            return 1
        
    def get_posts_in_page(self, soup: BeautifulSoup) -> list[Post]:
        posts: list[Post] = []
        
        cells = soup.find_all("div", class_ = "message-cell--main")
        cells = cells[:-1] # Last cell = message box
        
        for cell in cells:
            post_date = self.get_post_date(cell)            
            external_links = self.get_post_external_links(cell)
            
            if not external_links:
                continue
            
            post = Post(
                created_at = post_date,
                external_links = external_links
            )
            self.post_map[post.id] = post
            
            posts.append(post)
            
        return posts
    
    def get_post_date(self, cell: Tag) -> datetime:
        attribution = cell.find("header", class_ = "message-attribution message-attribution--split")
        time = attribution.find("time", class_ = "u-dt")
        timestamp = time.get("data-timestamp")
        
        return datetime.fromtimestamp(int(timestamp))
    
    def get_post_external_links(self, cell: Tag) -> dict[str, list[str]]:
        external_links: dict[str, list[str]] = defaultdict(list)
        
        content = cell.find("div", class_ = "message-content")
        link_elements = content.find_all("a", class_ = "link--external")
        
        for link_element in link_elements:
            href = link_element.get("href")
            if not is_valid_url(href):
                continue
            
            parsed: ParseResult = urlparse(href)
            if parsed.netloc not in SUPPORTED_SITES:
                continue
                        
            match parsed.netloc:
                case "goonbox.cr":
                    img_element = link_element.find("img")
                    
                    if not img_element:
                        external_links[parsed.netloc].append(href)
                        continue
                    
                    img_src = img_element.get("src")
                    img_src = img_src.replace(".md", "")
                    
                    external_links[parsed.netloc].append(img_src)
                    continue

            external_links[parsed.netloc].append(href)
        
        return to_dict(external_links)
    
    def sort_posts_by_domain(self, thread: Thread):
        domain_index: defaultdict[str, defaultdict[UUID, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        for post in thread.posts:
            for domain, url in post.external_links.items():
                domain_index[domain][post.id].extend(url)

        return to_dict(domain_index)