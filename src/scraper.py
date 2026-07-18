import base64
from collections import defaultdict
from datetime import datetime, timezone
import logging
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed, Future

from bs4 import BeautifulSoup, Tag

from config import Config
from domains import DOMAINS
from duplication import Duplication
from enums import RequestType, ResponseType
from models import Thread, Link, Post, DuplicationResult
from session.session import Session
from session.models import Request
from util import format_bytes
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


def get_thread(link: str, page: BeautifulSoup) -> Thread | None:
    def get_id() -> int | None:
        id_str = link.split(".")[-1]

        try:
            return int(id_str)

        except ValueError:
            return None

    def get_username() -> str:
        usr = link.split("/")[-1].split(".")[0]
        items = usr.split("-")
        titled = [item.title() for item in items[:2]]

        return unquote(" ".join(titled).strip())

    def get_tags() -> list[str]:
        labels = page.find_all("span", {"class": "label"})
        texts: list[str] = []

        for label in labels:
            text = label.get_text(strip = True)
            texts.append(text)

        return texts

    id = get_id()
    if not id:
        return None

    username = get_username()
    tags = get_tags()

    return Thread(id, username, tags)


def get_max_page_num(page: BeautifulSoup) -> int:
    main_nav = page.find("ul", {"class": "pageNav-main"})
    if not main_nav: return 1

    navs = main_nav.find_all("li", {"class": "pageNav-page"})
    last_nav = navs[-1] # Max page num

    try:
        return int(last_nav.get_text(strip = True))

    except ValueError:
        return 1


def get_posts(page: BeautifulSoup) -> tuple[dict[int, Post], list[Link]] | None:
    def get_links_in_cell(post_id: int, post_cell: Tag) -> list[Link]:
        cell_links = []

        # Handle external links first
        external_links = post_cell.find_all("a", {"class": "link--external"})

        for external_link in external_links:
            href = external_link.get("href")
            if not isinstance(href, str): continue
            parsed = urlparse(href)
            domain = parsed.netloc

            signed = None
            if "goonbox.cr" in href and "/img/" in href:
                # Get goonbox signed URL
                img = external_link.find("img")
                if not img: continue
                signed = img.get("src")
                if not isinstance(signed, str): continue
                signed = signed.replace(".md", "")

            # Decode redirects if present (base64)
            if "/redirect/" in href:
                encoded = parse_qs(parsed.query)["to"][0]
                decoded = base64.urlsafe_b64decode(
                    encoded + "=" * (-len(encoded) % 4)
                ).decode("utf-8")
                href = decoded
                parsed = urlparse(href)
                domain = parsed.netloc

            cell_links.append(Link(post_id, href, domain, signed))

        # Handle embeds
        embeds = post_cell.find_all("iframe", {"class": "saint-iframe"})

        for embed in embeds:
            src = embed.get("src")
            if not isinstance(src, str): continue
            parsed = urlparse(src)
            domain = parsed.netloc

            signed = None
            if "turbo.cr" in src and "/embed/" in src:
                src = src.replace("/embed/", "/v/")

            cell_links.append(Link(post_id, src, domain, signed))

        return cell_links

    def get_post_in_cell(post_cell: Tag) -> Post | None:
        # Retrieve the ID
        user_content = post_cell.find("div", {"class": "message-userContent"})
        if not user_content: return None

        post_id_str = user_content.get("data-lb-id")
        if not isinstance(post_id_str, str): return None
        id_str = post_id_str.split("-")[-1]

        try:
            id = int(id_str)

        except ValueError:
            return None

        # Retrieve posted at
        time = post_cell.find("time", {"class": "u-dt"})
        if not time: return None
        timestamp_str = time.get("data-timestamp")
        if not isinstance(timestamp_str, str): return None

        try:
            timestamp = int(timestamp_str)

        except ValueError:
            return None

        date = datetime.fromtimestamp(timestamp, tz = timezone.utc)

        return Post(id, date)

    posts: dict[int, Post] = {}
    links = []

    cells = page.find_all("div", {"class": "message-cell--main"})
    cells = cells[:-1] # Last cell = message box

    for cell in cells:
        post = get_post_in_cell(cell)
        if not post: return None
        posts[post.id] = post

        post_links = get_links_in_cell(post.id, cell)
        links.extend(post_links)

    return posts, links


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
            thread = get_thread(thread_link, page)
            if not thread:
                self.logger.warning(f"Failed to get thread: {thread_link}")
                continue

            # Get max page number to recurse through pages
            max_page_num = get_max_page_num(page)
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
                    : page_num for page_num in range(1, max_page_num + 1)
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

                    self.logger.info(f"{f'{counter}/{max_page_num}':<10} {thread_link}")
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

        page_posts = get_posts(page)
        if not page_posts:
            self.logger.warning(f"Failed to get posts: {thread_link}")
            return {}, []

        page_posts, page_links = page_posts

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