import logging
from urllib.parse import quote, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from requests import HTTPError

from .site import Site

class Bunkr(Site):
    def __init__(self, *args, **kwargs):
        super().__init__(logger = logging.getLogger("site.bunkr"), *args, **kwargs)
    
    def scrape(self):
        if "/a/" in self.url:
            self.handle_album()
        
        if "/f/" in self.url:
            self.handle_file()
    
    def handle_album(self):
        page = self.session.get(self.url)
        a_elements = page.find_all("a", class_ = "after:absolute after:z-10 after:inset-0")
        
        file_srcs: list[str] = []
        
        # Get file URLs in album
        for a_element in a_elements:
            href = a_element.get("href")
            file_url = "https://" + self.parsed.netloc + href

            file_srcs.append(file_url)

        with ThreadPoolExecutor(max_workers = 5, thread_name_prefix = "site.bunkr.thread") as executor:
            futures = [
                executor.submit(self.handle_file, file_src)
                for file_src in file_srcs
            ]
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                
                except Exception as e:
                    self.logger.exception(f"Error handling video: {e}")
                    continue
                
    def handle_file(self, url: str):
        page = self.session.get(url, self.url)
        button = page.find("a", class_ = "btn-main")
        href = button.get("href")
        signed = self.sign(href)
        
        try:
            self.download_file(signed)
        
        except HTTPError:
            self.logger.error(f"Failed to download {url}")
        
    
    def sign(self, url: str):
        self.logger.info(f"Signing file: {url}")
        
        id = url.split("/")[-1]        
        meta = self.session.post(
            url = "https://dl.bunkr.cr/api/_001_v2",
            payload = {"id": id},
            referer = self.url,
            origin = "https://dl.bunkr.cr"
        )
        
        raw_url = meta["mediafiles"] + meta["path"]
        path = quote(urlparse(raw_url).path)
        
        sign = self.session.get_json(
            url = "https://glb-apisign.cdn.cr/sign",
            referer = self.url,
            params = {"path": path}
        )
        
        signed_url = (
            f"{raw_url}"
            f"?n={meta['original']}"
            f"&token={sign['token']}"
            f"&ex={sign['ex']}"
        )
        
        self.logger.info(f"Signed URL: {signed_url}")
        
        return signed_url