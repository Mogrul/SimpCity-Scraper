from urllib.parse import urlparse
import logging
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup, Tag
from tqdm import tqdm

from .websites import WEBSITES
from .web import Web
from .models import ExternalURL
from .util import is_valid_url, get_domain_name
from .duplication import Duplication

from src.shared.config import Config

class SimpCity:
    def __init__(self):
        self.logger = logging.getLogger("simpcity")
        self.notified_unsupported: set[str] = set()

        self.config = Config()
        self.config.urls = self._clean_urls()
        
        self.web = Web()
        self.duplication = Duplication()
            
    # Init funcs 
    def _clean_urls(self) -> list[str]:
        """Removes garbage and unsupported URLs

        Returns:
            list[str]: A list of sanitised URLs
        """
        
        scrapable_urls = []
        
        for url in self.config.urls:
            scheme = urlparse(url).scheme
            domain_name = get_domain_name(url)

            if (
                    not scheme in ("http", "https")
                    and not domain_name
            ):
                self.logger.warning(f"Skipping invalid site: {url}")
                continue
            
            if (
                    domain_name not in WEBSITES
                    and domain_name not in self.notified_unsupported
            ):    
                self.logger.warning(f"Unsupported site: {domain_name}")
                self.notified_unsupported.add(domain_name)
                continue
            
            if url.endswith("/"):
                url = url[:-1]
                
            scrapable_urls.append(url)

        return scrapable_urls
    
    # Main function
    def scrape(self):
        """Scraping function to initate scraping of SimpCity threads
        """
        def get_page(
                url: str,
                page_num: int,
                username: str,
                thread_tags: list[str]
        ) -> list[ExternalURL] | None:
            page_url = self._get_page_url(url, page_num)
            
            soup = self.web.get(
                page_url,
                referer = url,
                log = False
            )
            
            if not isinstance(soup, BeautifulSoup):
                return
            
            page_urls = self._get_urls_in_page(
                soup,
                username,
                thread_tags
            )
            
            return page_urls
        
        for url in self.config.urls:
            username = self._get_username(url).capitalize()
            soup = self.web.get(url)
            
            if not isinstance(soup, BeautifulSoup):
                continue
            
            max_page_count = self._get_max_page_count(soup)
            thread_tags = self._get_thread_tags(soup)
            
            thread_path = Path(
                self.config.output,
                thread_tags[0],
                username
            )
            
            urls: list[ExternalURL] = []
            
            self.logger.info(f"Retrieving pages in {url}")
            with ThreadPoolExecutor(
                    max_workers = self.config.workers,
                    thread_name_prefix = "simpcity.page.thread"
            ) as executor:
                futures = [
                    executor.submit(get_page, url, page_num, username, thread_tags)
                    for page_num in range(1, max_page_count + 1)
                ]
                
                with tqdm(
                        total = len(futures),
                        desc = "Getting thread pages"
                ) as progress:
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                        
                        except Exception as e:
                            self.logger.error(f"Error grabbing page: {e}")
                            progress.update(1)
                            continue
                        
                        if not result:
                            progress.update(1)
                            continue
                        
                        urls.extend(result)
                        progress.update(1)
            
            domain_index = self._sort_urls_by_domain(urls)
            self._scrape_domains(domain_index)
            
            # Removes empty directories
            self.remove_empty_dirs()
            
            # Check for duplicates
            if self.config.remove_image_duplicates:
                self.duplication.check_duplicate_images(
                    thread_path
                )
            
            if self.config.remove_video_duplicates:
                self.duplication.check_duplicate_videos(
                    thread_path
                )

    def remove_empty_dirs(self):
        deleted = 0
        
        for directory in sorted(
                self.config.output.rglob("*"),
                key = lambda p: len(p.parts),
                reverse = True
        ):
            if directory.is_dir():
                try:
                    directory.rmdir() # only removes if empty
                    deleted += 1
                    
                except OSError:
                    pass # Contains files

        if deleted == 0:
            return

        self.logger.info(f"Deleted {deleted} empty directories in {self.config.output}")

    # Called after urls found
    def _scrape_domains(
            self,
            domain_index: dict[str, list[ExternalURL]]
    ):  
        """Passes external links to downloaders using a domain index.

        Args:
            domain_index (dict[str, list[ExternalURL]]): Index of str, list[] ("goonbox": [])
        """
        for domain in domain_index.keys():
            if domain not in WEBSITES:
                continue
            
            site = WEBSITES.get(domain)
            
            if not site:
                self.logger.error(f"Failed to get site from domain {domain}")
                continue
            
            urls = domain_index[domain]
            
            site = site(urls)
            site.scrape()
            
            self.remove_empty_dirs()

    # Domain scraping helper func
    def _sort_urls_by_domain(
            self,
            urls: list[ExternalURL]
    ) -> dict[str, list[ExternalURL]]:
        """Sorts the list of URLs retrieved on a thread scrape into an index of domain: list[url]

        Args:
            urls (list[ExternalURL]): List of URL objects retrieved from the thread scrape.

        Returns:
            dict[str, list[ExternalURL]]: A sorted dictionary of domain: list[] ("goonbox": [])
        """
        domain_index: defaultdict[str, list[ExternalURL]] = defaultdict(list)
        
        for url in urls:
            domain_name = url.domain_name
            
            domain_index[domain_name].append(url)

        return domain_index

    # Main URL extraction
    def _get_urls_in_page(
            self,
            soup: BeautifulSoup,
            username: str,
            thread_tags: list[str]
    ) -> list[ExternalURL]:
        """Extracts URL objects from a page in a thread.

        Args:
            soup (BeautifulSoup): HTML data retrieved from page request.
            username (str): Name of the Thread (usually username).
            thread_tags (list[str]): A list of tags in a thread.

        Returns:
            list[ExternalURL]: A list of URL objects on the page
        """
        urls: list[ExternalURL] = []
        
        cells = soup.find_all("div", class_ = "message-cell--main")
        cells = cells[:-1] # Last cell = message box
        
        for cell in cells:
            post_date = self._get_post_date(cell)            
            page_urls = self._get_urls_in_post(
                cell,
                post_date,
                username,
                thread_tags
            )
            
            if not page_urls:
                continue
            
            urls.extend(page_urls)
            
        return urls

    # URL extraction helpers
    def _get_post_date(
            self,
            cell: Tag,
    ) -> datetime:
        """Retrieves the date of a post in a page

        Args:
            cell (Tag): Tag of the post in a page

        Returns:
            datetime: date and time of when a post was created.
        """
        attribution = cell.find("header", class_ = "message-attribution message-attribution--split")
        
        if not attribution: return datetime.now()
        time = attribution.find("time", class_ = "u-dt")
        
        if not time: return datetime.now()
        timestamp = time.get("data-timestamp")
        
        if not isinstance(timestamp, str):
            return datetime.now()
        
        try:
            timestamp = int(timestamp)
        
        except ValueError:
            return datetime.now()

        return datetime.fromtimestamp(int(timestamp))

    def _get_username(
            self,
            url: str
    ) -> str:
        """Retrieves the thread name, usually username.

        Args:
            url (str): URL to the thread (simpcity.cr/threads/belledelphine)

        Returns:
            str: Username extracted from the URL
        """
        thread_name = url.split("/")[-1]
        username = thread_name.split("-")[0]
        
        return username
    
    def _get_page_url(
            self,
            url: str,
            page_num: int
    ) -> str:
        """Retrieves a URL with a page argument to use in requests.

        Args:
            url (str): URL entry point to the thread.
            page_num (int): Page number argument to add.

        Returns:
            str: URL entry point + page number argument
        """
        return url + f"/page-{page_num}"
    
    def _get_max_page_count(
            self,
            soup: BeautifulSoup
    ) -> int:
        """Retrieves the total amount of pages in a thread.

        Args:
            soup (BeautifulSoup): HTML object retrieved from a page request.

        Returns:
            int: The total amount of pages in a thread.
        """
        page_navs_main = soup.find("ul", class_ = "pageNav-main")
        
        if not page_navs_main:
            return 1
        
        page_navs = page_navs_main.find_all("li", class_ = "pageNav-page")
        last_page_nav = page_navs[-1]
        content = last_page_nav.get_text()
        
        try:
            return int(content)
        
        except KeyError:
            return 1

    def _get_urls_in_post(
            self,
            cell: Tag,
            created_at: datetime,
            username: str,
            thread_tags: list[str]
    ) -> list[ExternalURL]:
        """Retrieves the external urls in a post from a page obejct.

        Args:
            cell (Tag): Post HTML element to search through.
            created_at (datetime): Date of when the post was created.
            username (str): Username of the thread.
            thread_tags (list[str]): Tags of a thread.

        Returns:
            list[ExternalURL]: A list of URL objects
        """
        
        external_urls: list[ExternalURL] = []
        
        content = cell.find("div", class_ = "message-content")
        if not content: return external_urls
        url_elements = content.find_all("a", class_ = "link--external")
        iframes = content.find_all("iframe", class_ = "saint-iframe")
        
        for url_element in url_elements:
            href = url_element.get("href")
            if not isinstance(href, str):
                continue
            
            if not is_valid_url(href):
                # Handle redirects
                if "/redirect/" in href:
                    href = url_element.get_text()
                    
                    if not href:
                        continue
                    
                else:
                    continue
            
            domain_name = get_domain_name(href)
            if domain_name not in WEBSITES:
                continue
                        
            match domain_name:
                case "goonbox":
                    img_element = url_element.find("img")
                    
                    if "goonbox" in self.config.excluded_domains:
                        continue
                    
                    if not img_element:
                        external_urls.append(ExternalURL(
                            created_at = created_at,
                            url = href,
                            domain_name = "goonbox",
                            username = username,
                            tags = thread_tags
                        ))

                        continue
                    
                    img_src = img_element.get("src")
                    
                    if not isinstance(img_src, str):
                        continue
                    
                    img_src = img_src.replace(".md", "")
                    
                    external_urls.append(ExternalURL(
                        created_at = created_at,
                        url = img_src,
                        domain_name = "goonbox",
                        username = username,
                        tags = thread_tags
                    ))
                    
                    continue
            
            if domain_name in self.config.excluded_domains:
                continue
            
            external_urls.append(ExternalURL(
                created_at = created_at,
                url = href,
                domain_name = domain_name,
                username = username,
                tags = thread_tags
            ))
                    
        for iframe in iframes:
            src = iframe.get("src")
            if not isinstance(src, str):
                continue
            
            domain_name = get_domain_name(src)
            
            if domain_name not in WEBSITES:
                continue
            
            if domain_name in self.config.excluded_domains:
                continue
            
            external_urls.append(ExternalURL(
                created_at = created_at,
                url = src,
                domain_name = domain_name,
                username = username,
                tags = thread_tags
            ))
                
        return external_urls
    
    def _get_thread_tags(
            self,
            soup: BeautifulSoup
    ) -> list[str]:
        """Retrieves a list of tag names in a thread.

        Args:
            soup (BeautifulSoup): HTML object of a retrieved page.

        Returns:
            list[str]: A list of tags on a thread.
        """
        tags = []
        thread_title = soup.find("h1", class_ = "p-title-value")
        
        if not thread_title:
            return tags
        
        tag_elements = thread_title.find_all("a", class_ = "labelLink")
        
        if not tag_elements:
            return tags
        
        for tag_element in tag_elements:
            span = tag_element.find("span", class_ = "label")
            if not span: continue
            
            tags.append(span.get_text())
        
        return tags