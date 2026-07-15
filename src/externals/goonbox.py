import logging

from src.simpcity.models import Post
from src.http.models import HTTPResponse, HTTPRequest
from src.http.enums import RequestType, ResponseType
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
    
    def on_submission(self, post: Post) -> list[HTTPResponse]:
        for external_url in post.external_urls:
            if "/img/" in external_url.url:
                return self.handle_file(post, external_url)
            
            elif "/a/" in external_url.url:
                return self.handle_album(post, external_url)
        
        return []
    
    def handle_file(self, post: Post, external_url: ExternalURL) -> list[HTTPResponse]:
        if not external_url.signed:
            return []
        
        download_response = self.download(post, external_url)
        if not download_response:
            return []
        
        return [download_response]
    
    def handle_album(self, post: Post, external_url: ExternalURL) -> list[HTTPResponse]:
        album_id = external_url.url.split("/a/")[-1].split(".")[-1]
        api_url = f"https://goonbox.cr/api/albums/{album_id}"
        
        request = HTTPRequest(
            url = api_url,
            request_type = RequestType.GET,
            response_type = ResponseType.DICT
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, dict):
            return []
        
        pagination = response.data.get("pagination")
        
        if not isinstance(pagination, dict):
            return []
        
        last_page = pagination.get("last_page", 1)
        
        downloaded: list[HTTPResponse] = []
        for page_num in range(1, last_page + 1):
            if page_num != 1:
                request = HTTPRequest(
                    url = f"{api_url}/images?page={page_num}",
                    request_type = RequestType.GET,
                    response_type = ResponseType.DICT
                )
                response = self._http_client.send(request)
                
            if not isinstance(response.data, dict):
                continue
            
            images = response.data.get("images")
            if not isinstance(images, list):
                continue
            
            for image in images:
                if not isinstance(image, dict):
                    continue
                
                signed_url = image.get("original_url")
                file_name = image.get("original_filename")
                
                if (
                    not isinstance(signed_url, str)
                    or not isinstance(file_name, str)
                ):
                    continue
                                
                new_external_url = ExternalURL(
                    url = external_url.url,
                    signed = signed_url,
                    file_name = file_name
                )
                
                download = self.download(post, new_external_url)
                
                if not download:
                    continue
                
                downloaded.append(download)
            
        return downloaded
                