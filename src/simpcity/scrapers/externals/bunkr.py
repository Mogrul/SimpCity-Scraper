import logging

from bs4 import BeautifulSoup

from src.simpcity.models import ExternalScraperData
from src.http.models import (
    HttpDownloadResponse,
    HttpGetRequest,
    HttpPostRequest,
    HttpPostResponse
)
from src.http.enums import ResponseType
from .external_scraper import ExternalScraper

class Bunkr(ExternalScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("external.bunkr"),
            thread_prefix = "bunkr.thread",
            *args,
            **kwargs
        )
    
    def on_scrape(
            self,
            data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse, ...] | None:
        super().on_scrape(data)
        
        if "/a/" in data.url:
            return self._handle_album(data)
        
        if "/f/" in data.url:
            return self._handle_file(data)
    
    def _handle_album(self, data: ExternalScraperData) -> tuple[HttpDownloadResponse, ...] | None:
        super()._handle_album(data)
        page = self._client.get(HttpGetRequest(
            url = data.url,
            referer = data.url
        ), ResponseType.SOUP)
        
        if page.status_code != 200:
            return
        
        if not isinstance(page.data, BeautifulSoup):
            return
        
        # Get max page number
        pagination = page.data.find("nav", class_ = "pagination")
        if not pagination:
            return
        
        pages = pagination.find_all("a")
        if not pages:
            return
        
        page = pages[-2] # Second from last = top page
        
        try:
            max_page_count = int(page.get_text())
        
        except KeyError:
            return
        
        urls: list[str] = []
        for page_num in range(1, max_page_count + 1):
            if page_num != 1:
                page = self._client.get(HttpGetRequest(
                    url = data.url + f"?page={page_num}",
                    referer = data.url
                ), ResponseType.SOUP)
                
                if page.status_code != 200:
                    continue
            
            if not isinstance(page.data, BeautifulSoup):
                continue
            
            items = page.data.find_all("div", class_ = "relative group/item theItem")
            
            for item in items:
                a = item.find("a")
                if not a:
                    continue
                
                href = a.get("href")
                if not isinstance(href, str):
                    continue
                
                urls.append(f"https://bunkr.cr{href}")
        
        responses: list[HttpDownloadResponse] = []
        for url in urls:
            scraper_data = ExternalScraperData(
                domain = data.domain,
                username = data.username,
                url = url,
                posted_at = data.posted_at,
                tags = data.tags
            )
            
            response = self._handle_file(scraper_data)
            
            if not response:
                continue
            
            responses.extend(response)
        
        return tuple(responses)
    
    def _handle_file(self, data: ExternalScraperData) -> tuple[HttpDownloadResponse] | None:
        super()._handle_file(data)
        page = self._client.get(HttpGetRequest(
            url = data.url,
            referer = data.url
        ), ResponseType.SOUP)
        
        if page.status_code != 200:
            return
        
        if not isinstance(page.data, BeautifulSoup):
            return
        
        button = page.data.find("a", class_ = "ic-download-01")
        if not button: return
        
        href = button.get("href")
        if not isinstance(href, str): return
        
        id = href.split("/")[-1]
        
        post_response = self._client.post(HttpPostRequest(
            url = "https://dl.bunkr.cr/api/_001_v2",
            payload = {
                "id": id
            }
        ))
        
        if post_response.status_code != 200:
            return
        
        if not isinstance(post_response.data, dict):
            return
        
        original_file_name = post_response.data.get("original")
        domain_name = post_response.data.get("mediafiles")
        domain_path = post_response.data.get("path")
        
        if (
            not original_file_name
            or not domain_path
            or not domain_name
        ):
            return
        
        # Sign the download
        sign_path = domain_path.split("/")[-1]
        sign_response = self._client.get(HttpGetRequest(
            url = (
                "https://glb-apisign.cdn.cr/sign?path=%2Fstorage%2Fmedia%2F"
                f"{sign_path}"
            )
        ), ResponseType.DICT)
        
        if sign_response.status_code != 200:
            return
        
        if not isinstance(sign_response.data, dict):
            return
        
        ex = sign_response.data.get("ex")
        token = sign_response.data.get("token")
        
        signed_url = (
            domain_name
            + domain_path
            + f"?n={original_file_name}"
            + f"&token={token}"
            + f"&ex={ex}"
        )
        
        external_data = ExternalScraperData(
            domain = data.domain,
            username = data.username,
            url = signed_url,
            posted_at = data.posted_at,
            file_name = original_file_name,
            tags = data.tags
        )
        
        return (self.download(external_data),)