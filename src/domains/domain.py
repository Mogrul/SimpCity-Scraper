import logging
import threading
from asyncio import FIRST_COMPLETED
from concurrent.futures import ThreadPoolExecutor, Future, wait
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
            token_required: bool = False,
    ):
        self.posts = posts
        self.links = links
        self.thread = thread
        self.name = name if name else "Domain"
        self.logger = logger if logger else logging.getLogger("domain")
        self.thread_prefix = self.name + ".thread"
        self.stop_event = threading.Event()
        self.token_required = token_required

        self.config = Config()
        self.session = Session()
        self.token = ""

        self.executor: ThreadPoolExecutor | None = None
        self.futures: dict[Future, Link] = {}
        self.future_lock = threading.Lock()

        if self.config.database.enabled:
            self.database = Database()

        self.downloaded = 0
        self.failed = 0
        self.duplicate = 0
        self.completed_links: dict[Path, str] = {}

    def run(self) -> DomainResult:
        links_to_download: list[Link] = []

        # Check links against completed in database if enabled
        if getattr(self, "database", False):
            skipped = 0
            for link in self.links:
                if (
                    link.link in self.database.completed
                    or link.link in self.database.duplicates
                ):
                    skipped += 1
                    self.duplicate += 1
                else:
                    links_to_download.append(link)

            self.logger.info(f"Skipped {skipped}/{len(self.links)} downloads (database)")

        else:
            links_to_download = self.links

        # Filter out any duplicates
        urls: set[str] = set()
        for link_to_download in links_to_download.copy():
            if link_to_download.link not in urls:
                urls.add(link_to_download.link)

            else:
                links_to_download.remove(link_to_download)

        # Check if there's a token to grab
        if self.token_required:
            self.token = self.get_token()

            if not self.token:
                self.logger.error(f"Failed to get token")
                return DomainResult(0, 0, 0, {})

            else:
                self.logger.info(f"Got token: {self.token}")

        # Dynamic thread executor that allows albums to submit work to
        with ThreadPoolExecutor(
            max_workers = self.config.thread_count,
            thread_name_prefix = self.thread_prefix
        ) as executor:
            self.executor = executor

            # Submit initial jobs
            for link in links_to_download:
                post = self.posts.get(link.post_id)

                if not post:
                    self.logger.warning(f"Failed to get post from ID: {link.post_id}")
                    continue

                future = executor.submit(
                    self.on_submission,
                    post,
                    link
                )

                with self.future_lock:
                    self.futures[future] = link


            # Keep processing futures until there's none left
            while True:
                with self.future_lock:
                    pending = dict(self.futures)

                if not pending:
                    break

                done, _ = wait(
                    pending,
                    return_when = FIRST_COMPLETED
                )

                # Handle futures completing
                for future in done:
                    with self.future_lock:
                        link = self.futures.pop(future, None)

                    if not link:
                        continue

                    try:
                        response = future.result()

                    except Exception as e:
                        self.logger.error(f"{link.link} failed: {e}")
                        continue

                    self.handle_response(response)

        # Invalidate executor on completion
        self.executor = None

        return DomainResult(
            downloaded = self.downloaded,
            duplicate = self.duplicate,
            failed = self.failed,
            completed_links = self.completed_links
        )

    def on_submission(self, post: Post, link: Link) -> DownloadResponse:
        pass

    def album(self, post: Post, link: Link) -> None:
        pass

    def file(self, post: Post, link: Link) -> DownloadResponse:
        return self.download(post, link)

    def get_token(self) -> str:
        pass

    def handle_response(self, response: DownloadResponse):
        # Likely an album, skip
        if not response:
            return

        if response.status_code == StatusCode.FAILED:
            self.failed += 1
            return

        if response.status_code in (
            StatusCode.FAILED_EXISTS,
            StatusCode.FAILED_PATH
        ):
            self.duplicate += 1
            return

        request = response.request
        time_taken = response.time_taken
        file_size = response.file_size

        if (
            not request
            or not time_taken
            or not file_size
        ):
            self.failed += 1
            return

        link = request.link
        destination = request.destination

        # Add to database if enabled
        if getattr(self, "database", False):
            self.database.add_completed(link)

        self.completed_links[destination] = link
        self.downloaded += 1

    def download(
            self,
            post: Post,
            link: Link,
            params: dict[str, str] | None = None,
            headers: dict[str, str] | None = None
    ) -> DownloadResponse:
        file_path = self.create_file_path(post, link)

        if not file_path:
            return DownloadResponse(status_code = StatusCode.FAILED_PATH)

        if file_path.exists():
            return DownloadResponse(status_code = StatusCode.FAILED_EXISTS)

        download_link = link.link if not link.signed else link.signed

        if getattr(self, "database", False):
            if (
                download_link in self.database.duplicates
                or download_link in self.database.completed
            ):
                return DownloadResponse(status_code = StatusCode.FAILED_EXISTS)

        r_params = {}
        r_headers = {}
        if params:
            for key, value in params.items():
                r_params[key] = value

        if headers:
            for key, value in headers.items():
                r_headers[key] = value

        request = DownloadRequest(
            link = download_link,
            destination = file_path,
            headers = r_headers,
            params = r_params
        )
        download = self.session.download(request)
        self.log_download(download)
        return download

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

    def log_download(self, response: DownloadResponse) -> None:
        request = response.request
        file_size = response.file_size
        time_taken = response.time_taken

        if response.status_code in (
            StatusCode.FAILED_EXISTS,
            StatusCode.FAILED_PATH,
            StatusCode.FAILED
        ):
            return

        if (
            not request
            or not file_size
            or not time_taken
        ):
            return

        self.logger.info(
            f"{format_bytes(file_size):<10}"
            f"{format_duration(time_taken):^10}"
            f"Downloaded: {request.destination}"
        )