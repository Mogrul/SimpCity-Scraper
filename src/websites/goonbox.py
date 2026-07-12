import logging
from urllib.parse import urlparse

from src.models import ExternalURL, DownloadResult
from .website import WebSite
from src.util import get_domain_name

class GoonBox(WebSite):
    def __init__(self, *args, **kwargs):
        super().__init__(
            logger = logging.getLogger("website.goonbox"),
            thread_name = "website.goonbox.thread",
            *args,
            **kwargs
        )
    
    def on_url_scrape(self, url: ExternalURL) -> list[DownloadResult] | None:
        super().on_url_scrape(url)
    
        if "/a/" in url.url:
            # Album
            return self.handle_album(url)
        
        result = self.handle_image(url)
        if not result: return None
        
        return [result]
        
    def handle_album(self, url: ExternalURL) -> list[DownloadResult]:
        album_id =  url.url.split("/a/")[1].split("/")[0]
        if "." in album_id:
            album_id = album_id.split(".")[-1]
        
        parsed = urlparse(url.url)
        api_url = "https://" + parsed.netloc + f"/api/albums/{album_id}"
        
        first_page = self.web.get(
            api_url,
            referer = url.url,
            return_dict = True
        )
        
        if not isinstance(first_page, dict):
            return []
        
        pagination = first_page.get("pagination", {})
        
        if not isinstance(pagination, dict):
            return []
        
        last_page = pagination.get("last_page")
        
        if not isinstance(last_page, int):
            last_page = 1
        
        downloaded: list[DownloadResult] = []
        for page_num in range(1, last_page + 1):
            page_data = first_page
            
            if page_num != 1:
                paged_url  = api_url + f"/images?page={page_num}"
                page_data  = self.web.get(
                    paged_url,
                    referer = url.url,
                    return_dict = True
                )
                
                if not isinstance(page_data , dict):
                    continue
            
            images = page_data.get("images")
            if not isinstance(images, list):
                continue

            for image in images:
                img_url = image.get("original_url")
                if not img_url:
                    return []
                
                external_url = ExternalURL(
                    created_at = url.created_at,
                    url = img_url,
                    domain_name = get_domain_name(url.url),
                    username = url.username,
                    tags = url.tags
                )
                
                download = self.handle_image(external_url)
                if not download: continue
                
                downloaded.append(download)
        
        return downloaded
    
    def handle_image(self, url: ExternalURL) -> DownloadResult | None:
        file_path = self.get_file_path(url)
        downloaded = self.web.download(
            url,
            destination = file_path
        )

        return downloaded
    