import logging
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.http.models import HTTPResponse, HTTPRequest
from src.http.enums import ResponseType, RequestType
from src.simpcity.models.external_url import ExternalURL

from .external import External

class Bunkr(External):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("bunkr"),
            thread_prefix = "bunkr.thread",
            *args,
            **kwargs
        )
    
    def on_submission(self, external_url: ExternalURL) -> list[HTTPResponse]:
        if "/a/" in external_url.url:
            return self.handle_album(external_url)
        
        elif "/f/" in external_url.url:
            return self.handle_file(external_url)
        
        elif "/v/" in external_url.url:
            return self.handle_file(external_url)
        
        return []
    
    def handle_album(self, external_url: ExternalURL) -> list[HTTPResponse]:
        # Get the page and extract the items from it
        request = HTTPRequest(
            url = external_url.url,
            request_type = RequestType.GET,
            response_type = ResponseType.SOUP
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, BeautifulSoup):
            return []
        
        max_page_num = self._get_album_max_page_num(response.data)
        
        # Recurse through pages and get files
        downloads: list[HTTPResponse] = []
        for page_num in range(1, max_page_num + 1):
            if page_num != 1:
                request = HTTPRequest(
                    url = external_url.url,
                    request_type = RequestType.GET,
                    response_type = ResponseType.SOUP,
                    params = {"page": page_num}
                )
                response = self._http_client.send(request)
            
            if not isinstance(response.data, BeautifulSoup):
                continue
            
            files = self._get_files_in_page(response.data)
            
            # Recurse through found files and download them
            for file in files:
                url = "https://" + urlparse(external_url.url).netloc + file
                external_data = ExternalURL(url)
                download = self.handle_file(external_data)
                
                if not download:
                    continue
                
                downloads.extend(download)
                
        return downloads
    
    def handle_file(self, external_url: ExternalURL) -> list[HTTPResponse]:
        # Get file ID from page
        file_id = self._get_file_id(external_url)
        
        if not file_id:
            return []
        
        # Get information from a POST request to sign the download
        request = HTTPRequest(
            url = "https://dl.bunkr.cr/api/_001_v2",
            request_type = RequestType.POST,
            response_type = ResponseType.DICT,
            payload = {
                "id": file_id
            }
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, dict):
            return []
        
        signed_domain = response.data.get("mediafiles")
        original_filename = response.data.get("original")
        signed_path = response.data.get("path")
        
        if (
            not isinstance(signed_domain, str)
            or not isinstance(original_filename, str)
            or not isinstance(signed_path, str)
        ): return []
        
        # Sign path
        request = HTTPRequest(
            url = "https://glb-apisign.cdn.cr/sign",
            request_type = RequestType.GET,
            response_type = ResponseType.DICT,
            params = {
                "path": signed_path
            }
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, dict):
            return []
        
        ex = response.data.get("ex")
        token = response.data.get("token")
        
        if (
            not isinstance(ex, int)
            or not isinstance(token, str)
        ): return []
        
        external_url.file_name = original_filename
        external_url.signed = signed_domain + signed_path
        
        downloaded = self.download(
            external_url,
            headers = {
                "referer": "https://dl.bunkr.cr/",
                "host": urlparse(signed_domain).netloc
            },
            params = {
                "n": original_filename,
                "token": token,
                "ex": ex
            }
        )
        
        if not downloaded:
            return []
        
        return [downloaded]
    
    def _get_file_id(self, external_url: ExternalURL) -> str | None:
        request = HTTPRequest(
            url = external_url.url,
            request_type = RequestType.GET,
            response_type = ResponseType.SOUP
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, BeautifulSoup):
            return
        
        a = response.data.find("a", class_ = "btn-main")
        if not a: return
        
        href = a.get("href")
        if not isinstance(href, str): return
        
        return href.split("/")[-1]
    
    def _get_album_max_page_num(self, soup: BeautifulSoup) -> int:
        pagination = soup.find("nav", class_ = "pagination")
        
        if not pagination: return 1
        
        pages = pagination.find_all("a")
        if not pages: return 1
        page = pages[-2] # Second to last = max page
        
        try:
            return int(page.get_text())
        
        except KeyError:
            return 1
    
    def _get_files_in_page(self, soup: BeautifulSoup) -> list[str]:
        hrefs: list[str] = []
        items = soup.find_all("div", class_ = "theItem")
        
        for item in items:
            a = item.find("a")
            if not a: continue
            
            href = a.get("href")
            if not isinstance(href, str): continue
            
            hrefs.append(href)
        
        return hrefs