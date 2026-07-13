import logging
from datetime import datetime, timezone

from bs4 import Tag

from ..models.post import Post
from .user_scraper import UserScraper

class PostScraper:
    def __init__(self):
        self._logger = logging.getLogger("scraper.post")
    
    @classmethod
    def scrape(cls, url: str, tag: Tag) -> Post | None:
        scraper = cls()
    
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
                
        post = Post(
            url = url,
            id = id,
            user = user,
            posted_at = posted_at
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
        pass
    
    def _get_user_section(self, tag: Tag) -> Tag | None:
        return tag.find("section", class_ = "message-user")