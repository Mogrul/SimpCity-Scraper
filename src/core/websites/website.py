from urllib.parse import urlparse
from pathlib import Path
import time
import logging

import requests

from src.core.models import Post
from src.core.session import Session
from src.core.duplication import Duplication
from src.core.util import get_path_of_file

class Website:
    def __init__(
            self,
            url: str,
            post: Post,
            username: str,
            logger: logging.Logger
    ):
        self.url = url
        self.post = post
        self.author = post.author
        self.username = username
        self.logger = logger
        
        self.parsed = urlparse(url)
        self.base_url = f"{self.parsed.scheme}://{self.parsed.hostname}"
        
        self.session = Session()
        self.duplication = Duplication()
    
    def download(self):
        pass
    
    def download_file(self, url: str, check_duplicate=True):
        filename = urlparse(url).path.split("/")[-1]
        file_path = get_path_of_file(self.post, filename, self.username)
        temp_file_path = file_path.with_suffix(file_path.suffix + ".temp")

        if file_path.exists():
            return

        file_path.parent.mkdir(parents=True, exist_ok=True)

        downloaded = temp_file_path.stat().st_size if temp_file_path.exists() else 0

        headers = {}
        mode = "wb"

        if downloaded:
            headers["Range"] = f"bytes={downloaded}-"
            mode = "ab"

        next_report = ((downloaded // (1024 * 1024)) + 1) * 1024 * 1024

        with requests.get(url, headers=headers, stream=True) as response:

            if response.status_code == 200 and downloaded:
                # Server ignored Range request, restart download
                downloaded = 0
                mode = "wb"
                next_report = 1024 * 1024

            elif response.status_code not in (200, 206):
                self.logger.warning(f"Failed with status {response.status_code}: {url}")
                return

            with open(temp_file_path, mode) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue

                    f.write(chunk)
                    downloaded += len(chunk)

                    if downloaded >= next_report:
                        self.logger.info(
                            f"Downloading {temp_file_path.name}: "
                            f"{downloaded / (1024 * 1024):.2f} MB"
                        )
                        next_report += 1024 * 1024

        temp_file_path.rename(file_path)

        if check_duplicate:
            self.duplication.check_duplicate_images(file_path.parent.parent)

        self.logger.info(f"Downloaded {url} -> {file_path}")