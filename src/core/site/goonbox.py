import logging
from urllib.parse import urlparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bs4 import Tag

from .site import Site
from src.core.enum.references import References

class GoonBox(Site):
    def __init__(self, *args, **kwargs):
        super().__init__(logger = logging.getLogger("site.goonbox"), *args, **kwargs)
    
    def scrape(self):
        # Search for references first
        if References.EXTERNAL_LINK in self.references:
            src = self.get_src_from_reference(self.references[References.EXTERNAL_LINK])
            
            if src:
                self.download_file(src)
        
        # Handle album
        album_id = self.get_album_id()
        parsed = urlparse(self.url)
        api_url = "https://" + parsed.netloc + f"/api/albums/{album_id}"
        
        # Get first page and max page count
        page = self.get_api_url_by_page(api_url, 1)
        max_page_count = self.get_max_page_count(page)
        
        if max_page_count == 0:
            return
        
        base_parent_site = None
        
        # For every page in the JSON reply        
        for page_num in range(1, max_page_count + 1):
            # Get new page JSON if not first page
            if page_num != 1:
                page = self.get_api_url_by_page(api_url, page_num)
            
            images: list[dict] | None = page.get("images")
            if not images:
                self.logger.warning(f"Failed to get images in page {page_num} for {api_url}")
                continue
            
            # For every image in the JSON response
            with ThreadPoolExecutor(max_workers = 5, thread_name_prefix = "site.goonbox.thread") as executor:
                futures = [
                    executor.submit(self.handle_image, image)
                    for image in images
                ]


                for future in as_completed(futures):
                    try:
                        result = future.result()

                    except Exception as e:
                        self.logger.exception(f"Error handling image: {e}")
                        continue
                    
                    if not result:
                        continue
                    
                    url, destination, base_parent = result
                    
                    if not base_parent_site:
                        base_parent_site = base_parent
    
    def handle_image(self, image: dict) -> tuple[str, Path]:
        if type(image) is not dict:
            return
        
        references = {
            References.DATE: self.get_image_date(image)
        }
        img_url = image.get("original_url")
        
        if not img_url:
            raise TypeError(
                f"Failed to get original_url from JSON response"
            )

        return self.download_file(img_url, references)
        
    def get_image_date(self, image: dict) -> datetime:
        created_at = image.get("created_at")
        
        if not created_at:
            created_at_date = datetime.now()

        else:
            created_at_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        
        return created_at_date
            
    def get_src_from_reference(self, reference: Tag) -> str | None:
        src_img = reference.find("img")
        if not src_img:
            # Is an album
            return
        
        src = src_img["data-url"]
        return src.replace(".md", "")

    def get_album_id(self) -> str:
        return self.url.split("/")[-1]
    
    def get_api_url_by_page(self, api_url: str, page_num: int) -> dict:
        api_url = api_url + f"/images?page={page_num}"
        
        reply = self.session.get_json(api_url, referer = self.url)
        if not reply:
            return
        
        return reply
    
    def get_max_page_count(self, reply: dict) -> int:
        if not reply:
            return 0
        
        pagination = reply.get("pagination")
        
        if not pagination:
            return 1
        
        last_page = pagination.get("last_page")
        return last_page if last_page else 1