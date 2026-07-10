import time
from urllib.parse import urlparse
from pathlib import Path
import logging

from bs4 import BeautifulSoup

from .website import Website
from src.core.models import Post
from src.core.util import get_path_of_file, split_into_groups

class GoonBox(Website):
    def __init__(self, url: str, post: Post, username: str):
        self.logger = logging.getLogger("website.goonbox")
        
        super().__init__(url, post, username, self.logger)
    
    def download(self):
        page = self.session.get(self.url, sleep = 2)
        
        if "img" in self.url:
            src = self.get_file_src(page)
            self.download_file(src)
            return
        
        self.session.scroll_to_bottom()
        
        card = page.select_one("div.grid.gap-3.grid-cols-2")
        item_groups = card.find_all("div", class_ = "relative group")
        
        direct_links: list[str] = []
        
        for item_group in item_groups:
            a = item_group.find("a", class_ = "block")
            href = a.get("href")
            
            direct_links.append(self.base_url + href)
        
        direct_links_grouped = split_into_groups(direct_links, 20)
        
        for direct_link_group in direct_links_grouped:
            for x in range(0, len(direct_link_group)):
                direct_link = direct_link_group[x]
                print(f"Opening {direct_link} in tab {x + 1}")
                self.session.open_in_tab(direct_link, x + 1)
            
            for x in range(0, len(direct_link_group)):
                direct_link = direct_link_group[x]
                
                page = self.session.get_tab_source(x)
                
                src = self.get_file_src(page)
                self.download_file(src)
        
        self.session.cleanup_tabs()
    
    def get_file_src(self, page: BeautifulSoup) -> str:
        div = page.find("div", class_ = "lg:w-2/3")
        img = div.find("img")
        src = img.get("src")
        
        return src