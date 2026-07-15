from collections import defaultdict
from urllib.parse import urlparse
from pathlib import Path
import logging

from src.shared import Config
from src.externals import EXTERNALS
from src.duplication.duplication import Duplication
from .models import Post, Thread, ExternalURL
from .scrapers import ThreadScraper

class SimpCity:
    def __init__(self):
        self._logger = logging.getLogger("SimpCity")
        self._config = Config()
    
    def run(self):
        urls = self._config.urls
        
        for url in urls:
            scraper = ThreadScraper()
            response = scraper.scrape(url)
       
            if not response: continue
            
            thread, posts = response
            
            self._logger.info(f"Found {len(posts)} posts in {thread.url}")
            self._pass_to_externals(thread, posts)
    
    def _pass_to_externals(self, thread: Thread, posts: list[Post]):
        results: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        
        for post in posts:
            domain_map: dict[str, list[ExternalURL]] = defaultdict(list)
            
            for external_url in post.external_urls:
                parsed = urlparse(external_url.url)
                
                domain_map[parsed.netloc].append(external_url)
            
            for domain, external_urls in domain_map.items():
                external = EXTERNALS.get(domain)
                
                if not external:
                    self._logger.error(f"Failed to get external from domain: {domain}")
                    continue
                
                external = external(thread, external_urls, post)
                result = external.run()
                
                for key, value in result.items():
                    results[domain][key] += value
        
        # Check for duplicates before logging downloads
        if self._config.check_duplicates:
            tags = thread.tags
            tag_path = (tags[0],) if tags else ()
            duplication = Duplication()
            duplication.check_duplicates(Path(
                self._config.download_location,
                *tag_path,
                thread.username
            ))
        
        # Log final results for each domain
        for domain, result in results.items():
            failed = result.get("failed", 0)
            existing = result.get("existing", 0)
            complete = result.get("complete", 0)
            marked_duplicate = result.get("marked_duplicate", 0)
            total = result.get("total", 0)
            
            self._logger.info(
                "\n"
                f"{domain}:\n"
                f"      {'Downloaded:':<12}{f'{complete}/{total}':>10}\n"
                f"      {'Existing:':<12}{f'{existing}/{total}':>10}\n"
                f"      {'Failed:':<12}{f'{failed}/{total}':>10}\n"
                f"      {'Marked:':<12}{f'{marked_duplicate}/{total}':>10}"
            )