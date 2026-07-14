import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from bs4 import Tag

from ..models import Post, ExternalURL
from src.externals import EXTERNALS

class PostScraper:
    def __init__(self):
        self._logger = logging.getLogger("simpcity.post")
    
    def scrape(self, post_tag: Tag, url: str) -> Post | None:
        external_links: list[ExternalURL] = []
        posted = self._get_posted(post_tag)
        id = self._get_id(post_tag)
        post_url = self._get_url(post_tag, url)
        
        if not posted:
            self._logger.error(f"Failed to extract date from post")
            self._logger.error(post_tag)
            return
        
        if not id:
            self._logger.error(f"Failed to get ID from post")
            return
        
        if not post_url:
            self._logger.error(f"Failed to extract URL from post")
            return
        
        # Extract links from the post tag
        external_links.extend(self._get_external_links(post_tag))
        external_links.extend(self._get_iframe_links(post_tag))
                
        # Build a post object and return it
        return Post(
            url = post_url,
            id = id,
            posted = posted,
            external_urls = external_links
        )
            
    def _get_goonbox_url(self, external_link_tag: Tag) -> str | None:
        img = external_link_tag.find("img")
        if not img: return
        
        src = img.get("src")
        if not isinstance(src, str): return
        
        return src.replace(".md", "")
    
    def _get_posted(self, post_tag: Tag) -> datetime | None:
        time_element = post_tag.find("time", class_ = "u-dt")
        if not time_element: return
        
        timestamp_str = time_element.get("data-timestamp")
        if not isinstance(timestamp_str, str): return
        
        try:
            timestamp = int(timestamp_str)
        
        except KeyError:
            return
        
        return datetime.fromtimestamp(timestamp, tz = timezone.utc)
    
    def _get_id(self, post_tag: Tag) -> int | None:
        div = post_tag.find("div", class_ = "message-userContent")
        if not div: return
        
        id_str = div.get("data-lb-id")
        if not isinstance(id_str, str): return
        
        stripped = id_str.split("-")[-1]
        
        try:
            return int(stripped)
        
        except KeyError:
            return
    
    def _get_url(self, post_tag: Tag, url: str) -> str | None:
        div = post_tag.find("div", class_ = "message-userContent")
        if not div: return
        
        id_str = div.get("data-lb-id")
        if not isinstance(id_str, str): return
        
        return url + f"/#{id_str}"

    def _get_external_links(self, post_tag: Tag) -> list[ExternalURL]:
        external_links: list[ExternalURL] = []
        
        external_link_tags = post_tag.find_all("a", class_ = "link link--external")
        for external_link_tag in external_link_tags:
            href = external_link_tag.get("href")
            
            if not isinstance(href, str):
                continue
            
            parsed = urlparse(href)
            
            if parsed.netloc not in EXTERNALS:
                continue
            
            signed = None
            
            if "goonbox" in href:
                signed = self._get_goonbox_url(external_link_tag)
            
            external_links.append(ExternalURL(
                url = href,
                signed = signed
            ))
        
        return external_links
    
    def _get_iframe_links(self, post_tag: Tag) -> list[ExternalURL]:
        external_links: list[ExternalURL] = []
        
        iframes = post_tag.find_all("iframe", class_ = "saint-iframe")
        for iframe in iframes:
            src = iframe.get("src")
            
            if not isinstance(src, str): continue
            
            parsed = urlparse(src)
            if parsed.netloc not in EXTERNALS:
                continue
            
            if "turbo.cr" in src and "/embed/" in src:
                src = src.split("/embed/")[-1]
                src = f"https://turbo.cr/v/{src}"

            external_links.append(ExternalURL(
                url = src
            ))
        
        return external_links