import logging
from datetime import datetime

from bs4 import Tag

from ..models import User

class UserScraper:
    def __init__(self):
        self._logger = logging.getLogger("scraper.user")
    
    @classmethod
    def scrape(cls, tag: Tag) -> User | None:
        scraper = cls()
    
        avatar_url = scraper._get_avatar_url(tag)
        username = scraper._get_username(tag)
        
        if not username:
            scraper._logger.error(f"Failed to get username from post!")
            return
        
        stats = scraper._get_stats(tag)
        
        if not stats:
            scraper._logger.error(f"Failed to extract stats from username: {username}")
            return
        
        joined_at, post_count, reactions_received = stats
        
        banners = scraper._get_banners(tag)
        id = scraper._get_id(tag)
        
        if not id:
            scraper._logger.error(f"Failed to get user ID from post!")
            return
        
        url = scraper._get_url(username, id)
        
        if not url:
            scraper._logger.error(f"Failed to get user URL from post!")
            return
        
        return User(
            id = id,
            url = url,
            username = username,
            joined_at = joined_at,
            post_count = post_count,
            reactions_received = reactions_received,
            avatar_url = avatar_url,
            banners = banners
        )
        
    def _get_avatar_url(self, tag: Tag) -> str | None:
        avatar_border = tag.find("span", class_ = "simp-avatar-border-wrap")
        
        if not avatar_border:
            return None
        
        a = avatar_border.find("a", class_ = "avatar avatar--m")
        
        if not a:
            return None
        
        img = a.find("img")
        
        if not img:
            return None
        
        src = img["src"]
        
        if not src:
            return None
        
        return str(src)

    def _get_username(self, tag: Tag) -> str | None:
        a = tag.find("a", class_ = "username")
        
        if not a:
            return None
        
        return a.get_text()
    
    def _get_stats(self, tag: Tag) -> tuple[datetime, int, int] | None:
        extras = tag.find("div", class_ = "message-userExtras")
        
        if not extras:
            return None
        
        dds = extras.find_all("dd")
        
        joined: datetime | None = None
        post_count: int | None = None
        reactions_received: int | None = None
        
        for i in range(len(dds)):
            dd = dds[i]
            text = dd.get_text()
            
            match i:
                case 0:
                    joined = datetime.strptime(text, "%b %d, %Y")
                
                case 1:
                    post_count = int(text.replace(",", ""))
                
                case 2:
                    reactions_received = int(text.replace(",", ""))
        
        if not joined:
            return None
        
        if not post_count:
            return None
        
        if not reactions_received:
            return None
        
        return (joined, post_count, reactions_received)
    
    def _get_banners(self, tag: Tag) -> list[str]:
        banners = tag.find_all("div", class_ = "userBanner")
        
        if not banners:
            return []
        
        banner_strs = []
        for banner in banners:
            banner_strs.append(banner.get_text().strip()[1:][:-1])
        
        return banner_strs
    
    def _get_id(self, tag: Tag) -> int | None:
        a = tag.find("a", class_ = "username")
        
        if not a:
            return None
        
        id_str = a["data-user-id"]
        
        try:
            id_str = str(id_str)
            return int(id_str)
        
        except KeyError:
            return None
    
    def _get_url(self, username: str, id: int) -> str:
        return f"https://simpcity.cr/members/{username}.{id}"