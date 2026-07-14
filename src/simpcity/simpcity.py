import logging
from collections import defaultdict
from urllib.parse import urlparse

from .scrapers import ThreadScraper
from .models import ExternalScraperData, Thread
from .scrapers.externals import EXTERNAL_SCRAPERS

class SimpCity:
    def __init__(self):
        self._logger = logging.getLogger("simpcity")
        self._notified_unsupported: set[str] = set()
    
    def scrape(self, url: str):
        if url.endswith("/"):
            url = url[:-1]
            
        thread = ThreadScraper.scrape(url)
        
        if not thread:
            self._logger.error(f"Failed to generate thread object from {url}")
            return

        self._scrape_thread(thread)

    def _scrape_thread(self, thread: Thread):
        download_counters: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        
        for page in thread.pages:
            page_map: dict[str, list[ExternalScraperData]] = defaultdict(list)
            
            # Sort posts to manageable map
            for post in page.posts:
                for external_url in post.external_urls:
                    parsed = urlparse(external_url)
                    domain = parsed.netloc
                    
                    if "cuckcapital" in domain:
                        domain = "goonbox.cr"
                    
                    # Skip unsupported
                    if domain not in EXTERNAL_SCRAPERS:
                        if domain not in self._notified_unsupported:
                            self._logger.warning(f"Unsupported domain: {domain}")
                            self._notified_unsupported.add(domain)
                        continue
                    
                    page_map[domain].append(ExternalScraperData(
                        domain = domain,
                        username = thread.username,
                        url = external_url,
                        posted_at = post.posted_at,
                        tags = thread.tags
                    ))
                
            # Pass maps to external scrapers.
            for domain in page_map.keys():
                external_scraper = EXTERNAL_SCRAPERS.get(domain)
                
                if not external_scraper:
                    self._logger.critical(f"Failed to get external scraper: {domain}")
                    return
                
                scraper_datas = page_map[domain]
                external_scraper = external_scraper(scraper_datas)
                (
                    downloaded,
                    failed,
                    total,
                    exists
                ) = external_scraper.scrape()
                
                download_counters[domain]["downloaded"] += downloaded
                download_counters[domain]["failed"] += failed
                download_counters[domain]["total"] += total
                download_counters[domain]["exists"] += exists
        
        for domain, values in download_counters.items():
            downloaded = values["downloaded"]
            failed = values["failed"]
            total = values["total"]
            exists = values["exists"]
            
            self._logger.info(
                "\n"
                f"{domain}\n"
                f"      {'Downloaded:':<12}{f'{downloaded}/{total}':>10}\n"
                f"      {'Exists:':<12}{f'{exists}/{total}':>10}\n"
                f"      {'Failed:':<12}{f'{failed}/{total}':>10}"
            )