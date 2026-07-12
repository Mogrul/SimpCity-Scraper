import logging

from bs4 import BeautifulSoup

from src.models import ExternalURL, DownloadResult
from .website import WebSite

class Bunkr(WebSite):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("website.bunkr"),
            thread_name = "website.bunkr.thread",
            *args,
            **kwargs
        )
    
    def on_url_scrape(self, url: ExternalURL) -> list[DownloadResult] | None:
        super().on_url_scrape(url)
        page = self.web.get(
            url.url,
            referer = "https://simpcity.cr"
        )
        
        if not isinstance(page, BeautifulSoup):
            return
        
        page_id = self.get_page_id(page)
        
        if not page_id: return
        
        signed = self.sign(url, page_id)
        
        if not signed: return
        
        file_path = self.get_file_path(url)
        url.url = signed
        downloaded = self.web.download(
            url,
            destination = file_path,
            referer = "https://bunkr.cr/"
        )
        
        if not downloaded:
            return []
        
        return [downloaded]
    
    def get_page_id(self, page: BeautifulSoup) -> str | None:
        button = page.find("a", class_ = "ic-download-01")
        
        if not button:
            return None
        
        href = button.get("href")
        
        if not isinstance(href, str):
            return None
        
        return href.split("/")[-1]
    
    def sign(self, url: ExternalURL, page_id: str) -> str | None:
        file_name = url.url.split("/")[-1]
        signing_url = (
            "https://glb-apisign.cdn.cr/sign?path=%2Fstorage%2Fmedia%2F"
            + file_name
        )
        
        reply = self.web.get(
            url = signing_url,
            referer = "https://dl.bunk.cr/",
            origin = "https://dl.bunkr.cr",
            return_dict = True
        )
        
        if not isinstance(reply, dict):
            return None
        
        token = reply.get("token")
        ex = reply.get("ex")
        
        if not token or not ex:
            return None
        
        post_url = "https://dl.bunkr.cr/api/_001_v2"
        payload = {
            "id": page_id
        }
        
        reply = self.web.post(
            post_url,
            payload,
            referer = url.url,
        )
        
        if not isinstance(reply, dict):
            return
        
        domain = reply.get("mediafiles")
        path = reply.get("path")
        
        if not domain or not path:
            return None
        
        return (
            domain
            + path
            + f"?token={token}"
            + f"&ex={ex}"  
        )