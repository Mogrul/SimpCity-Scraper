import logging
from urllib.parse import urlparse

from .website import WebSite

class Turbo(WebSite):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("website.turbo"),
            *args,
            **kwargs
        )
    
    def scrape(self): 
        for link, created_at in self.link_map.items():
            signed = self.sign(link)
            
            file_path = self.get_file_path(signed, created_at)
            self.web.download(
                urlparse(signed),
                destination = file_path,
                return_dict = True
            )
    
    def sign(self, url: str):
        def get_embed_id() -> str:
            return url.split("/")[-1]
        
        api_url = "https://turbo.cr/api/sign?v=" + get_embed_id()
        data = self.web.get(
            urlparse(api_url),
            referer = urlparse(url),
            return_dict = True
        )
        
        if isinstance(data, dict):
            if data.get("success", False):
                return data["url"]
        
        return None