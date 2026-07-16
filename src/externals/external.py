import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid5, NAMESPACE_URL
import subprocess

from src.simpcity.models import (
    Thread, ExternalURL,
    Post, DomainStats
)
from src.http.models import HTTPResponse, HTTPRequest
from src.http.enums import (
    RequestType, ResponseType,
    StatusCode
)
from src.http.client import HTTPClient
from src.database.database import Database
from src.database.models import ExtractedItem
from src.shared import Config

class External:
    def __init__(
            self,
            
            # SimpCity args
            thread: Thread,
            domain: str,
            posts: list[Post],
            post_by_id: dict[int, Post],
            
            # External subclass args
            logger: logging.Logger | None = None,
            thread_prefix: str | None = None
    ):
        # External subclass args
        self._thread_prefix = thread_prefix if thread_prefix else "external.thread"
        self._logger = logger if logger else logging.getLogger("external")
        
        # SimpCity args
        self._thread = thread
        self._domain = domain
        self._posts = posts
        self._post_by_id = post_by_id
        
        self._database = Database()
        self._config = Config()
        self._http_client = HTTPClient()
    
    def run(self) -> DomainStats:
        marked_extracted = 0
        marked_duplicate = 0
        
        existing = 0
        
        extracted = 0
        downloaded = 0
        failed = 0
        
        with ThreadPoolExecutor(
            max_workers = self._config.network.workers,
            thread_name_prefix = self._thread_prefix
        ) as executor:
            futures = [
                executor.submit(self.on_submission, post)
                for post in self._posts
            ]
            
            for future in as_completed(futures):
                try:
                    responses = future.result()
                
                except Exception as e:
                    self._logger.error(f"Error on submission: {e}")
                    failed += 1
                    continue
                
                for response in responses:
                    # If the download path already exists
                    if response.status_code == StatusCode.DUPLICATE_DOWNLOAD.value:
                        existing += 1
                        continue
                    
                    # If download was marked as already extracted
                    if response.status_code == StatusCode.ALREADY_EXTRACTED.value:
                        marked_extracted += 1
                        continue
                    
                    # If download was marked as a duplicate file
                    if response.status_code == StatusCode.MARKED_DUPLICATE.value:
                        marked_duplicate += 1
                        continue
                    
                    # If the HTTP request failed
                    if response.status_code != 200:
                        failed += 1
                        continue
                    
                    # If there's no data in the response
                    if not isinstance(response.data, dict):
                        failed += 1
                        continue
                    
                    destination = response.data.get("destination", Path())
                    file_size = response.data.get("file_size", 0)
                    time_taken = response.data.get("time_taken", .0)
                    post_id = response.data.get("post_id")
                    
                    # If there's no post_id in response
                    if not post_id:
                        failed += 1
                        continue
                    
                    # Log successful download
                    self._logger.info(
                        f"{self._format_bytes(file_size):<10}"
                        f"{self._format_duration(time_taken):^10}"
                        f"Downloaded: {destination}"
                    )
                    
                    downloaded += 1
                    
                    # Attempt extraction
                    if self._config.scraper.extract_files:
                        for extract_response in self._attempt_extraction(
                                post_id,
                                response,
                                destination
                        ):
                            if not extract_response.status_code == StatusCode.EXTRACTED.value:
                                continue
                            
                            if not isinstance(extract_response.data, dict):
                                continue
                            
                            extract_destination = extract_response.data.get("destination", Path)
                            extract_file_size = extract_response.data.get("file_size", 0)
                            
                            self._logger.info(
                                f"{self._format_bytes(extract_file_size):<10}"
                                f"{'':^10}"
                                f"Extracted: {extract_destination}"
                            )
                            
                            extracted += 1
        
        return DomainStats(
            marked_extracted,
            marked_duplicate,
            extracted,
            downloaded,
            failed,
            existing,
            total = (
                marked_extracted
                + marked_duplicate
                + extracted
                + downloaded
                + failed
                + existing
            )
        )
                      
    def on_submission(self, post: Post) -> list[HTTPResponse]:
        return []
    
    def handle_album(self, post: Post, external_url: ExternalURL) -> list[HTTPResponse]:
        return []
    
    def handle_file(self, post: Post, external_url: ExternalURL) -> list[HTTPResponse]:
        return []
    
    def download(
            self,
            post: Post,
            external_url: ExternalURL,
            params: dict | None = None,
            headers: dict | None = None
    ) -> HTTPResponse | None:
        file_path = self._get_file_path(post, external_url)
        
        if not file_path:
            self._logger.error(f"Failed to generate file path from: {external_url}")
            return
        
        request = HTTPRequest(
            url = external_url.url if not external_url.signed else external_url.signed,
            request_type = RequestType.DOWNLOAD,
            response_type = ResponseType.DOWNLOAD,
            params = params,
            headers = headers,
            payload = {
                "destination": file_path,
                "post_id": post.id
            }
        )
        
        if file_path in self._database.duplicate_items:
            return HTTPResponse(
                request = request,
                status_code = StatusCode.MARKED_DUPLICATE.value
            )
        
        if file_path in self._database.extracted_items:
            return HTTPResponse(
                request = request,
                status_code = StatusCode.ALREADY_EXTRACTED.value
            )
        
        return self._http_client.send(request)
        
    def _get_file_path(self, post: Post, external_url: ExternalURL) -> Path | None:
        url = external_url.url
        signed = external_url.signed
        tags = self._thread.tags
        username = self._thread.username
        base_path = self._config.scraper.download_location
        posted = post.posted
        
        if "?" in url:
            url = url.split("?")[0]
        
        if not external_url.file_name:
            url_path = url.split("/")[-1]
            if "." not in url_path:
                if not signed:
                    return
                
                # Attempt to get from signed
                external_url.file_name = signed.split("/")[-1]
            
            else:
                external_url.file_name = url.split("/")[-1]
            
        file_id = str(
            uuid5(NAMESPACE_URL, url + external_url.file_name)
        ).replace("-", "")[:-16]
        original_file_path = Path(external_url.file_name)
        tag_path = (tags[0],) if tags else ()
        
        thread_path = Path(
            base_path,
            *tag_path,
            username
        )
        
        post_path = Path(
            str(posted.year),
            str(posted.strftime("%B"))
        )
        
        file_name = Path(
            f"[{posted.year}-{posted.month:02d}-{posted.day:02d}] "
            f"{file_id}{original_file_path.suffix}"
        )
        
        return thread_path / post_path / file_name
    
    def _format_bytes(self, amount: int) -> str:
        value = float(amount)
    
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if value < 1024:
                return f"{value:.2f} {unit}"
                    
            value /= 1024

        return f"{value:.2f} PB"
    
    def _format_duration(self, seconds: float) -> str:
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.3f}s"
        elif seconds < 3600:
            minutes, seconds = divmod(seconds, 60)
            return f"{int(minutes)}m {seconds:.1f}s"
        elif seconds < 86400:
            hours, remainder = divmod(seconds, 3600)
            minutes = remainder // 60
            return f"{int(hours)}h {int(minutes)}m"
        else:
            days, remainder = divmod(seconds, 86400)
            hours = remainder // 3600
            return f"{int(days)}d {int(hours)}h"
    
    def _attempt_extraction(
            self,
            post_id: int,
            response: HTTPResponse,
            destination: Path
    ) -> list[HTTPResponse]:
        post = self._post_by_id[post_id]
        
        if not isinstance(post, Post):
            self._logger.error(f"Failed to get post by id: {post_id}")
            return []
        
        tags = self._thread.tags
        username = self._thread.username
        tag_path = (tags[0],) if tags else ()
        
        temp_path = Path(
            self._config.scraper.download_location,
            *tag_path,
            username,
            "temp"
        )
        
        result = subprocess.run(
            [
                str(self._config.scraper.extractor_location),
                "x",
                str(destination),
                f"-o{temp_path}",
                "-y"
            ],
            capture_output = True,
            text = True
        )
        
        # On extraction fail - not an archive
        if result.returncode != 0:
            return []
        
        # On success
        # Add extracted item to database
        self._database.add_extracted(ExtractedItem(destination))
        
        # Delete archive
        destination.unlink()
        
        # Rename and move extracted files
        responses = []
        for file in temp_path.rglob("*"):
            if not file.is_file():
                continue
            
            external_url = ExternalURL(
                url = response.request.url,
                file_name = file.name
            )
            
            new_path = self._get_file_path(post, external_url)
            if not new_path:
                continue
            
            try:
                # Already extracted
                file.rename(new_path)
            except FileExistsError:
                return []

            responses.append(
                HTTPResponse(
                    request = response.request,
                    status_code = StatusCode.EXTRACTED.value,
                    data = {
                        "destination": new_path,
                        "file_size": new_path.stat().st_size,
                    },
                )
            )
        
        # Remove empty directories
        for directory in sorted(
            temp_path.rglob("*"),
            key=lambda p: len(p.parts),
            reverse=True
        ):
            if directory.is_dir():
                directory.rmdir()

        # Remove the root temp folder
        temp_path.rmdir()
        
        return responses