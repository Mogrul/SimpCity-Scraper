from collections import defaultdict
import logging
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed, Future

from bs4 import BeautifulSoup, Tag

from config import Config
from domains import DOMAINS
from duplication import Duplication, DuplicationResult
from enums import RequestType, ResponseType
from . import ThreadScraper, PostScraper
from .models import *
from session import Request, Session
from shared.util import format_bytes
from domains import DomainResult

def normalise_thread_link(link: str) -> str | None:
    parsed = urlparse(link)
    parts = parsed.path.split('/')

    # Find /thread/{name}
    try:
        index = parts.index("threads")
        thread = parts[index + 1]

    except (ValueError, IndexError):
        return None

    return f"{parsed.scheme}://{parsed.netloc}/threads/{thread}"


class Scraper:
    def __init__(self):
        self.logger = logging.getLogger("Scraper")
        self.config = Config()
        self.session = Session()

        self.domain_results: dict[str, DomainResult] = {}
        self.duplication_results: dict[Path, DuplicationResult] = {}

    def run(self):
        thread_links = self.config.links

        for thread_link in thread_links:
            thread_link = normalise_thread_link(thread_link)

            if not thread_link:
                self.logger.warning(f"Failed to normalise thread link: {thread_link}")
                continue

            # Get first page to retrieve thread data
            page = self.get_page(thread_link, 1)
            if not page:
                self.logger.warning(f"Failed to get page: {thread_link}")
                continue

            # Get thread data from first page
            thread = ThreadScraper(page, thread_link).scrape()
            if not thread:
                self.logger.warning(f"Failed to get thread: {thread_link}")
                continue

            # Get max page number to recurse through pages
            posts: dict[int, Post] = {}
            links: list[Link] = []
            with ThreadPoolExecutor(
                max_workers = self.config.thread_count,
                thread_name_prefix = "scrape.page"
            ) as executor:
                counter = 1
                # Future -> page num
                futures: dict[Future, int] = {
                    executor.submit(self.run_page, thread_link, page_num)
                    : page_num for page_num in range(1, thread.max_page_num + 1)
                }

                for future in as_completed(futures.keys()):
                    page_num = futures[future]

                    try:
                        result = future.result()

                    except Exception as e:
                        self.logger.error(f"Failed to get page {page_num} in thread {thread_link}: {e}")
                        return

                    page_posts, page_links = result
                    links.extend(page_links)
                    for key, value in page_posts.items():
                        posts[key] = value

                    self.logger.info(f"{f'{counter}/{thread.max_page_num}':<10} {thread_link}")
                    counter += 1

            self.logger.info(f"Found {len(posts)} posts, {len(links)} links in {thread_link}")
            completed_links = self.pass_to_domains(thread, posts, links)

            # Build thread path to check for duplicates if enabled
            if (
                self.config.duplication.images
                or self.config.duplication.videos
            ):
                tag_path = (thread.tags[0],) if thread.tags else ()
                thread_path = Path(
                    self.config.downloads.location,
                    *tag_path,
                    thread.username
                )
                duplication = Duplication(thread_path, completed_links)
                if self.config.duplication.images:
                    result = duplication.check_images()
                    if result:
                        self.duplication_results[thread_path] = result

                if self.config.duplication.videos:
                    result = duplication.check_videos()
                    if result:
                        if thread_path in self.duplication_results:
                            self.duplication_results[thread_path] += result

                        else:
                            self.duplication_results[thread_path] = result

        # Log the finished domain results
        self.log_results()

    def run_page(self, thread_link: str, page_num: int) -> tuple[dict[int, Post], list[Link]]:
        page = self.get_page(thread_link, page_num)
        if not page:
            self.logger.warning(f"Failed to get page: {thread_link}")
            return {}, []

        posts = PostScraper(page).scrape()
        if not posts:
            self.logger.warning(f"Failed to get posts: {thread_link}")
            return {}, []

        page_posts, page_links = posts

        return page_posts, page_links

    def get_page(self, link: str, page_num = 1) -> BeautifulSoup | None:
        request = Request(f"{link}/page-{page_num}", RequestType.GET, ResponseType.SOUP)
        response = self.session.send(request)

        if not isinstance(response.data, BeautifulSoup):
            return None

        return response.data

    def pass_to_domains(
            self,
            thread: Thread,
            posts: dict[int, Post],
            links: list[Link]
    ) -> dict[Path, str]:
        link_map: dict[str, list[Link]] = defaultdict(list) # domain -> list[link]
        completed_links: dict[Path, str] = {}

        # Sort links by their domain
        for link in links:
            if link.domain in self.config.downloads.skip_domains:
                continue

            if link.domain not in DOMAINS:
                continue

            link_map[link.domain].append(link)

        for domain, links in link_map.items():
            self.logger.debug(f"{domain} -> {len(links)} links")

        # Each domain gets a list of links to download
        for domain, links in link_map.items():
            domain_cls = DOMAINS.get(domain)

            if not domain_cls:
                self.logger.error(f"Failed to find domain for {domain}")
                return completed_links

            domain_cls = domain_cls(posts, links, thread)
            domain_result = domain_cls.run()

            for key, value in domain_result.completed_links.items():
                completed_links[key] = value

            # Collect results
            if domain in self.domain_results:
                self.domain_results[domain] += domain_result

            else:
                self.domain_results[domain] = domain_result

        return completed_links

    def log_results(self):
        for path, result in self.duplication_results.items():
            self.logger.info(
                f"{path}:\n"
                f"{'Deleted:':<20}{f'{result.deleted_count}':>15}\n"
                f"          {'Saved:':<20}{f'{format_bytes(result.bytes_saved)}':>15}\n"
            )

        for domain, result in self.domain_results.items():
            total = result.downloaded + result.failed + result.duplicate

            self.logger.info(
                f"{domain}:\n"
                f"          {'Downloaded':<20}{f'{result.downloaded}/{total}':>15}\n"
                f"          {'Duplicate':<20}{f'{result.duplicate}/{total}':>15}\n"
                f"          {'Failed':<20}{f'{result.failed}/{total}':>15}"
            )