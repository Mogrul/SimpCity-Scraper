import logging
from datetime import datetime, timezone

from bs4 import Tag, BeautifulSoup

from ..models.post import Post
from .user_scraper import UserScraper
from src.http.http_client import HttpClient
from src.http.models.request import HttpRequest
from src.shared.config import Config

class PostScraper:
    def __init__(self):
        self._logger = logging.getLogger("scraper.post")
        self._client = HttpClient()
        self._config = Config()
    
    @classmethod
    def scrape(cls, url: str, tag: Tag) -> Post | None:
        scraper = cls()

        user = None
        if scraper._config.save_metadata:
            user_section = scraper._get_user_section(tag)
            if not user_section:
                scraper._logger.error(f"Failed to get user section for post!")
                return
            
            user = UserScraper.scrape(user_section)
            
            if not user:
                scraper._logger.error(f"Failed to scrape user from post!")
                return
    
        posted_at = scraper._get_date(tag)
        if not posted_at:
            scraper._logger.error(f"Failed to get posted_at for post!")
            return
        
        id = scraper._get_id(tag)
        if not id:
            scraper._logger.error(f"Failed to get ID for post!")
            return
        
        unpaged_url = scraper._get_unpaged_url(url)
        url = scraper._get_url(unpaged_url, id)
        external_urls = scraper._get_external_urls(tag)
                
        post = Post(
            url = url,
            id = id,
            user = user,
            posted_at = posted_at,
            external_urls = external_urls
        )
        
        return post
    
    def _get_date(self, tag: Tag) -> datetime | None:
        time_element = tag.find("time", class_ = "u-dt")
        if not time_element:
            return None
        
        timestamp = time_element["data-timestamp"]
        
        try:
            timestamp = str(timestamp)
            timestamp = int(timestamp)
        
        except KeyError:
            return None
        
        return datetime.fromtimestamp(timestamp, tz = timezone.utc)

    def _get_id(self, tag: Tag) -> int | None:
        id = tag["data-content"]
        
        if not id: return None
        
        try:
            id = str(id)
            return int(id.replace("post-", ""))
        
        except KeyError:
            return None
    
    def _get_url(self, url: str, id: int) -> str:
        return url + f"/#post-{id}"
    
    def _get_unpaged_url(self, url: str) -> str:
        return url.split("/page-")[0]
    
    def _get_external_urls(self, tag: Tag) -> list[str]:
        external_urls = []
        
        # Search classes with link--external
        externals = tag.find_all("a", class_ = "link link--external")
        for external in externals:
            href = external["href"]
            
            if not isinstance(href, str): continue
            
            href = href.strip()
            
            if "/redirect/" in href:
                href = self._get_redirect_url(href)
            
            elif (
                "https://goonbox.cr" in href
                and not "/album/" in href
            ):
                href = self._get_goonbox_url(external)
            
            if not href:
                continue
            
            external_urls.append(href)
        
        # Search IFrames for embedded stuff
        iframes = tag.find_all("iframe", class_ = "saint-iframe")
        for iframe in iframes:
            src = iframe.get("src")
            
            if not src: continue
            
            external_urls.append(src)
        
        return external_urls
    
    def _get_user_section(self, tag: Tag) -> Tag | None:
        return tag.find("section", class_ = "message-user")

    def _get_redirect_url(self, href: str) -> str | None:
        url = "https://simpcity.cr" + href
        
        response = self._client.get(HttpRequest(
            url = url,
            referer = "https://simpcity.cr"
        ))
        
        if (
            response.status_code != 200
            or not isinstance(response.data, BeautifulSoup)
        ):
            return None
        
        target_link_el = response.data.find("a", class_ = "simpLinkProxy-targetLink")
        
        if not target_link_el:
            return None
        
        target_link = target_link_el["href"]
        
        if not target_link or not isinstance(target_link, str):
            return None
        
        return target_link
    
    def _get_goonbox_url(self, tag: Tag) -> str | None:
        img = tag.find("img")
        
        if not img: return None
        
        src = img.get("src")
        
        if (
            not src
            or not isinstance(src, str)
        ):
            return None
        
        return src.replace(".md", "")