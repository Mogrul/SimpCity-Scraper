import logging
from urllib.parse import urljoin, urlparse, quote

import requests

from .website import Website
from src.core.models import Post

class Bunkr(Website):
    def __init__(
            self,
            url: str,
            post: Post,
            username: str
    ):
        self.logger = logging.getLogger("website.bunkr")
        
        super().__init__(url, post, username, self.logger)
    
    def download(self):
        if "/a/" in self.url:
            self.handle_album(self.url)
        
        if "/f/" in self.url:
            self.handle_file(self.url)
    
    def handle_album(self, url: str):
        page = self.session.get(url)
        
        file_as = page.find_all("a", class_ = "after:absolute after:z-10 after:inset-0")
                
        file_srcs: list[str] = []
        
        # Get file urls in album
        for file_a in file_as:
            href = file_a.get("href")
            file_url = self.base_url + href
        
            file_srcs.append(file_url)
        
        for file_src in file_srcs:
            self.handle_file(file_src)
    
    def handle_file(self, url: str):
        page = self.session.get(url)
        
        button = page.find("a", class_ = "btn-main")
        href = button.get("href")

        id = href.split("/")[-1]
        
        self.logger.info(f"Signing file: {href}")
        
        req_s = requests.session()
        req_s.headers = {
            "User-Agent": self.session.execute_script("return navigator.userAgent;"),
            "Referer": self.url,
            "Content-Type": "application/json",
            "Origin": "https://dl.bunkr.cr",
            "Accept-Encoding": "gzip, deflate, br, zstd"
        }
        
        meta = req_s.post(
            "https://dl.bunkr.cr/api/_001_v2",
            json = {"id": id}
        )
        
        meta = meta.json()
        
        raw_url = meta["mediafiles"] + meta["path"]
        
        path = quote(urlparse(raw_url).path)
        
        sign = req_s.get(
            "https://glb-apisign.cdn.cr/sign",
            params = {"path": path}
        ).json()
        
        signed_url = (
            f"{raw_url}"
            f"?n={meta['original']}"
            f"&token={sign['token']}"
            f"&ex={sign['ex']}"
        )

        self.logger.info(f"Signed URL: {signed_url}")
        
        self.download_file(signed_url, check_duplicate = False)