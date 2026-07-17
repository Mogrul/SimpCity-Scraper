import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from config import Config
from database import Database
from enums import StatusCode
from models import Post, Link, DownloadResponse, DownloadRequest, Thread, DomainResult
from session import Session
from util import format_bytes, format_duration


class Domain:
    def __init__(
            self,
            posts: dict[int, Post],
            links: list[Link],
            thread: Thread,
            name: str | None = None,
            logger: logging.Logger | None = None,
    ):
        self.posts = posts
        self.links = links
        self.thread = thread
        self.name = name if name else "Domain"
        self.logger = logger if logger else logging.getLogger("domain")
        self.thread_prefix = self.name + ".thread"

        self.config = Config()
        self.session = Session()

        if self.config.database.enabled:
            self.database = Database()

    def run(self) -> DomainResult:
        downloaded = 0
        failed = 0
        duplicate = 0

        links_to_download = []

        # Check links against completed in database if enabled
        if self.database:
            skipped = 0
            for link in self.links:
                if not link.link in self.database.completed:
                    links_to_download.append(link)
                else:
                    skipped += 1
                    duplicate += 1

            self.logger.info(f"Skipped {skipped}/{len(self.links)} downloads (database)")

        else:
            links_to_download = self.links

        # Store completed downloads [url -> list[Downloads]]
        completed_links: dict[str, list[DownloadResponse]] = defaultdict(list)

        with ThreadPoolExecutor(
            max_workers = self.config.thread_count,
            thread_name_prefix = self.thread_prefix
        ) as executor:
            futures: dict[Future, Link] = {}

            for link in links_to_download:
                post = self.posts[link.post_id]

                if not post:
                    self.logger.warning(f"Failed to get post from ID: {link.post_id}")
                    continue

                futures[executor.submit(self.on_submission, post, link)] = link

            # Handle futures completing
            for future in as_completed(futures.keys()):
                link = futures[future]

                try:
                    responses = future.result()

                except Exception as e:
                    self.logger.error(f"{link.link} failed: {e}")
                    failed += 1
                    continue

                if not responses:
                    failed += 1
                    continue

                if self.database:
                    self.database.add_completed(link.link)

                for response in responses:
                    # Handle status codes
                    if response.status_code in (
                            StatusCode.FAILED,
                            StatusCode.FAILED_PATH
                    ):
                        failed += 1
                        continue

                    if response.status_code == StatusCode.FAILED_EXISTS:
                        duplicate += 1
                        continue

                    file_size = response.file_size
                    time_taken = response.time_taken
                    request = response.request

                    if (
                            not file_size
                            or not time_taken
                            or not request
                    ):
                        self.logger.error(f"Failed to download file from ID: {link.post_id}")
                        failed += 1
                        continue

                    destination = request.destination
                    completed_links[link].append(destination)
                    self.logger.info(
                        f"{format_bytes(file_size):<10}"
                        f"{format_duration(time_taken):^10}"
                        f"Downloaded: {destination}"
                    )
                    downloaded += 1

        return DomainResult(
            downloaded = downloaded,
            duplicate = duplicate,
            failed = failed,
            completed_links = completed_links
        )

    def on_submission(self, post: Post, link: Link) -> list[DownloadResponse]:
        pass

    def album(self, post: Post, link: Link) -> list[DownloadResponse]:
        pass

    def file(self, post: Post, link: Link) -> DownloadResponse:
        pass

    def download(self, post: Post, link: Link) -> DownloadResponse:
        file_path = self.create_file_path(post, link)

        if not file_path:
            return DownloadResponse(status_code = StatusCode.FAILED_PATH)

        if file_path.exists():
            return DownloadResponse(status_code = StatusCode.FAILED_EXISTS)

        download_link = link.link if not link.signed else link.signed
        return self.session.download(DownloadRequest(download_link, file_path))

    def create_file_path(self, post: Post, link: Link) -> Path | None:
        file_link = link.link
        file_name = link.filename

        if "?" in file_link:
            file_link = file_link.split("?")[0]

        if not file_name:
            file_link = file_link.split("/")[-1]
            if "." not in file_link:
                if not link.signed:
                    return None

                file_name = link.signed.split("/")[-1]

            else:
                file_name = file_link.split("/")[-1]

        link.filename = file_name

        file_id = str(
            uuid5(NAMESPACE_URL, file_link + file_name)
        ).replace("-", "")[:-16]
        original_file_path = Path(file_name)
        tag_path = (self.thread.tags[0],) if self.thread.tags else ()

        thread_path = Path(
            self.config.downloads.location,
            *tag_path,
            self.thread.username
        )

        post_path = Path(
            str(post.date.year),
            str(post.date.strftime("%B"))
        )

        file_path = Path(
            f"[{post.date.year}-{post.date.month:02d}-{post.date.day:02d}] "
            f"{file_id}{original_file_path.suffix}"
        )

        return thread_path / post_path / file_path