import logging
from urllib.parse import urlparse

from src.http.models import HTTPResponse, HTTPRequest
from src.http.enums import RequestType, ResponseType
from src.simpcity.models.external_url import ExternalURL
from src.simpcity.models.post import Post

from .external import External

class Turbo(External):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("turbo"),
            thread_prefix = "turbo.thread",
            *args,
            **kwargs
        )
    
    def on_submission(self, post: Post) -> list[HTTPResponse]:
        super().on_submission(post)
        responses: list[HTTPResponse] = []
        
        for external_url in post.external_urls:
            if "/v/" in external_url.url:
                responses.extend(self.handle_file(post, external_url))
        
        return responses
    
    def handle_file(
            self,
            post: Post,
            external_url: ExternalURL
    ) -> list[HTTPResponse]:
        file_id = self.get_id(external_url)
        
        # Sign the ID
        request = HTTPRequest(
            url = f"https://{self._domain}/api/sign",
            request_type = RequestType.GET,
            response_type = ResponseType.DICT,
            params = {
                "v": file_id
            }
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, dict):
            return []
        
        signed_url = response.data.get("url")
        file_name = response.data.get("filename")
        
        if (
            not isinstance(signed_url, str)
            or not isinstance(file_name, str)
        ): return []
        
        external_url.file_name = file_name
        external_url.signed = signed_url
        
        downloaded = self.download(post, external_url)
        
        if not downloaded:
            return []
        
        return [downloaded]
    
    def handle_album(
            self,
            post: Post,
            external_url: ExternalURL
    ) -> list[HTTPResponse]:
        return []
    
    def get_id(self, external_url: ExternalURL) -> str:
        return external_url.url.split("/")[-1]