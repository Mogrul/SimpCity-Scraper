import logging
from datetime import datetime, timedelta

from bs4 import BeautifulSoup, Tag

from .site import Site
from src.core.util import get_domain_name
from src.core.enum.references import References

class SimpCity(Site):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("site.simpcity"),
            *args,
            **kwargs
        )
        
        self.username = self.get_username()
        self.references[References.USERNAME] = self.username
    
    def scrape(self):
        super().scrape()
        
        main_page = self.session.get(self.url)
        max_page_count = self.get_page_max_count(main_page)
        
        self.logger.info(f"Found {max_page_count} page/s in {self.url}")
        
        for page_num in range(1, max_page_count + 1):
            if page_num == 1:
                page = main_page
            else:
                page = self.get_page_with_count(self.url, page_num)
            
            if not page:
                self.logger.error(f"Failed to get page #{page_num}: {self.url}")
                continue
            
            self.scrape_posts(page)

    def scrape_posts(self, page: BeautifulSoup):
        posts = page.find_all("div", class_ = "message-cell--main")
        posts = posts[:-1] # Last post = message box
        
        post_contents: list[Tag] = []
        
        for post in posts:
            self.references[References.POST] = post
            post_date = self.get_post_date(post)
            self.references[References.DATE] = post_date
            message_content = post.find("div", class_ = "message-main")
            
            if message_content:
                post_contents.append(message_content)
            
            external_link_as = message_content.find_all("a", class_ = "link--external")
            for external_link_a in external_link_as:
                self.references[References.EXTERNAL_LINK] = external_link_a
                external_link = external_link_a.get("href")
                domain_name = get_domain_name(external_link)
                
                if domain_name.startswith("/"):
                    continue
                
                if domain_name not in self.sites:
                    self.logger.warning(f"Site not supported ({domain_name}): {external_link}")
                    continue
                
                site = self.sites.get(domain_name)
                self.site = site(
                    external_link,
                    self.sites,
                    self.session,
                    references = self.references
                )
                self.site.scrape()
    
    def get_page_with_count(
            self,
            url: str,
            page_num: int
    ) -> BeautifulSoup:
        if url.endswith("/"):
            url = url + f"page-{page_num}"
        
        else:
            url = url + f"/page-{page_num}"
        
        return self.session.get(url)
    
    def get_page_max_count(self, page: BeautifulSoup) -> int:
        page_navs = page.find_all("li", class_ = "pageNav-page")
        
        if not page_navs:
            return 1
        
        last_nav = page_navs[-1]
        last_nav_text = last_nav.get_text()
        
        try:
            return int(last_nav_text)
        
        except TypeError:
            self.logger.error(f"Failed to convert page_nav_text {last_nav_text} to int")
            return 1

    def get_username(self) -> str:
        split = self.url.split("/")
        
        if self.url.endswith("/"):
            split = split[-2]
        
        else:
            split = split[-1]
        
        username = split.split("-")[0]
        
        return username
    
    def get_post_date(self, post: Tag) -> datetime:
        header = post.find("header", class_ = "message-attribution")
        time = header.find("time", class_ = "u-dt")
        time_str = time.get_text().replace(",", "")
        
        try:
            post_date = datetime.strptime(time_str, "%b %d %Y")
        
        except ValueError:
            now = datetime.now()
            
            if time_str.startswith("Today at "):
                time_part = time_str.removeprefix("Today at ")
                t = datetime.strptime(time_part, "%I:%M %p").time()
                post_date = datetime.combine(now.date(), t)

            elif time_str.startswith("Yesterday at "):
                time_part = time_str.removeprefix("Yesterday at ")
                t = datetime.strptime(time_part, "%I:%M %p").time()
                post_date = datetime.combine(now.date() - timedelta(days=1), t)

            else:
                day_name, time_part = time_str.split(" at ")
                t = datetime.strptime(time_part, "%I:%M %p").time()

                target_weekday = datetime.strptime(day_name, "%A").weekday()
                days_ago = (now.weekday() - target_weekday) % 7

                post_date = datetime.combine(
                    now.date() - timedelta(days=days_ago),
                    t
                )
        
        return post_date
        