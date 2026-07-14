import logging

from src.http.models import HTTPResponse
from src.simpcity.models.external_url import ExternalURL

from .external import External

class GoonBox(External):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("goonbox"),
            thread_prefix = "goonbox.thread",
            *args,
            **kwargs
        )
    
    def on_submission(self, external_url: ExternalURL) -> list[HTTPResponse]:
        if "/img/" in external_url.url:
            return self.handle_file(external_url)
        
        return []
    
    def handle_file(self, external_url: ExternalURL) -> list[HTTPResponse]:
        if not external_url.signed:
            return []
        
        download_response = self.download(external_url)
        if not download_response:
            return []
        
        return [download_response]