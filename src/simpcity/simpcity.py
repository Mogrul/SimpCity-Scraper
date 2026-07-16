from collections import defaultdict
from urllib.parse import urlparse
from concurrent.futures import (
    ThreadPoolExecutor, as_completed,
    Future
)
from pathlib import Path
import logging
from copy import copy

from src.shared import Config
from src.externals import EXTERNALS
from src.duplication.duplication import Duplication
from .models import (
    Post, Thread,
    ExternalURL, DomainStats
)
from .scrapers import ThreadScraper

class SimpCity:
    def __init__(self):
        self._logger = logging.getLogger("SimpCity")
        self._config = Config()
    
    def run(self):
        urls = self._config.urls
        global_stats: dict[str, DomainStats] = {}
        
        for url in urls:
            scraper = ThreadScraper()
            response = scraper.scrape(url)
       
            if not response: continue
            
            thread, posts = response
            
            self._logger.info(f"Found {len(posts)} posts in {thread.url}")
            thread_domain_stats = self._pass_to_externals(thread, posts)
            
            # Add stats to global stats
            for domain, stats in thread_domain_stats.items():
                if domain in global_stats:
                    global_stats[domain] += stats
                else:
                    global_stats[domain] = stats
            
            tag_path = (thread.tags[0],) if thread.tags else ()
            user_path = Path(
                self._config.scraper.download_location,
                *tag_path,
                thread.username
            )
            
            # Nothing downloaded
            if not user_path.exists():
                continue
            
            # Cleanup empty directories
            self._cleanup(user_path)
            
            # Check for duplicates
            if (
                    self._config.duplication.images
                    or self._config.duplication.videos
            ):
                duplication = Duplication()
                duplication.check_duplicates(user_path)
            
        # Log stats
        self._log_domain_stats(global_stats)
    
    def _pass_to_externals(
            self,
            thread: Thread,
            posts: list[Post]
    ) -> dict[str, DomainStats]:
        def handle_domain(
                domain: str,
                domain_posts: list[Post],
                post_by_id: dict[int, Post]
        ) -> tuple[str, DomainStats] | None:
            external = EXTERNALS.get(domain)
            
            if not external:
                self._logger.critical(f"Domain {domain} not found in externals")
                return

            external = external(
                thread,
                domain,
                domain_posts,
                post_by_id
            )
            
            return (domain, external.run())
                
        domain_map: dict[str, list[Post]] = defaultdict(list)
        post_by_id: dict[int, Post] = {}

        # Make sure post urls match domain
        for post in posts:
            posts_by_domain: dict[str, list[ExternalURL]] = defaultdict(list)
            post_by_id[post.id] = post

            for external_url in post.external_urls:
                domain = urlparse(external_url.url).netloc
                posts_by_domain[domain].append(external_url)

            for domain, urls in posts_by_domain.items():
                filtered_post = copy(post)
                filtered_post.external_urls = urls

                domain_map[domain].append(filtered_post)

        domain_stats: dict[str, DomainStats] = {}
        domain_count = len(domain_map.keys())
        
        # Each domain gets their own thread.
        with ThreadPoolExecutor(
                max_workers = 1 if domain_count == 0 else domain_count,
                thread_name_prefix = "domain.thread"
        ) as executor:
            futures: list[Future] = []
            
            # Submit all futures
            for domain, domain_posts in domain_map.items():
                if domain not in EXTERNALS:
                    self._logger.critical(f"Domain {domain} not found in externals")
                    continue
                
                if domain in self._config.scraper.skip_scrapers:
                    continue
                
                futures.append(executor.submit(
                    handle_domain,
                    domain,
                    domain_posts,
                    post_by_id
                ))
            
            # Handle futures completing
            for future in as_completed(futures):
                try:
                    result = future.result()
                
                except Exception as e:
                    self._logger.exception(f"Exception on domain: {e}")
                    continue
                
                if not result:
                    continue
                
                domain, stats = result
                domain_stats[domain] = stats
        
        return domain_stats
    
    def _log_domain_stats(
            self,
            domain_stats: dict[str, DomainStats]
    ):
        for domain, stats in domain_stats.items():
            self._logger.info(
                "\n"
                f"{domain}:\n"
                f"      {'Downloaded':<20}{f'{stats.downloaded}/{stats.total}':>15}\n"
                f"      {'Extracted:':<20}{f'{stats.extracted}/{stats.total}':>15}\n"
                f"      {'Existing:':<20}{f'{stats.existing}/{stats.total}':>15}\n"
                f"      {'Failed:':<20}{f'{stats.failed}/{stats.total}':>15}\n"
                f"      {'Marked Duplicate:':<20}{f'{stats.marked_duplicate}/{stats.total}':>15}\n"
                f"      {'Marked Extracted:':<20}{f'{stats.marked_extracted}/{stats.total}':>15}"
            )
    
    def _cleanup(
            self,
            path: Path
    ):
        # Cleans up empty directories
        for directory in sorted(
            path.rglob("*"),
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()

        # Finally remove the root if it's empty
        if not any(path.iterdir()):
            path.rmdir()