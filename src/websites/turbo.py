import logging
from urllib.parse import urlparse

from .website import WebSite

class Turbo(WebSite):
    def __init__(self, *args, **kwargs):
        logger = kwargs.get("logger")
        if not logger:
            logger = logging.getLogger("website.turbo")
        
        super().__init__(
            logger = logger,
            *args,
            **kwargs
        )
    
    def scrape(self): 
        for link, created_at in self.link_map.items():
            signed = self.sign(link)
            
            if not signed: continue
            
            file_path = self.get_file_path(signed, created_at)
            self.web.download(
                signed,
                destination = file_path,
                return_dict = True
            )
    
    def sign(self, url: str) -> str | None:
        def get_embed_id() -> str:
            return url.split("/")[-1]
        
        api_url = "https://turbo.cr/api/sign?v=" + get_embed_id()
        data = self.web.get(
            api_url,
            referer = url,
            return_dict = True
        )
        
        if isinstance(data, dict):
            if data.get("success", False):
                return data["url"]
        
        return None