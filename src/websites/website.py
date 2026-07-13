import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid5, NAMESPACE_URL
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

from src.models import ExternalURL, DownloadResult
from src.web import Web
from src.shared.config import Config

class WebSite:
    def __init__(
            self,
            urls: list[ExternalURL],
            logger: logging.Logger | None = None,
            thread_name = "WebSite"
    ):
        self.urls = urls
        self.thread_name = thread_name
        self.logger = (
            logging.getLogger(__name__)
            if not logger else logger
        )
        self.config = Config()

        self.web = Web()
            
    def scrape(self): 
        with ThreadPoolExecutor(
                max_workers = self.config.workers,
                thread_name_prefix = self.thread_name
        ) as executor:
            future_to_url = {
                executor.submit(self.on_url_scrape, url): url
                for url in self.urls
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]

                try:
                    results = future.result()
                except Exception as e:
                    self.logger.error(f"Error downloading {url}: {e}")
                    continue
                
                if not results: continue
                
                for result in results:
                    extracted = self.attempt_extraction(result)
                    
                    if extracted:
                        for extract_result in extracted:
                            self.logger.info(f"Extracted {extract_result.url.url} -> {extract_result.path}")
                    
                    else:
                        self.logger.info(f"Downloaded {result.url.url} -> {result.path}")
            
    def on_url_scrape(self, url: ExternalURL) -> list[DownloadResult] | None:
        pass
    
    def get_file_path(self, url: ExternalURL):
        def get_file_name() -> Path:
            file_name = parsed.path.replace("/", "")
            
            if "?" in file_name:
                file_name = file_name.split("?")[0]
            
            return Path(file_name)
        
        parsed = urlparse(url.url)
        
        if url.file_name:
            file_name = url.file_name
            
            file_id = str(
                uuid5(NAMESPACE_URL, parsed.geturl() + file_name.name)
            ).replace("-", "")[:-16]
            
        else:
            file_name = get_file_name()
        
            file_id = str(
                uuid5(NAMESPACE_URL, parsed.geturl())
            ).replace("-", "")[:-16]
        
        tag_path = (url.tags[0],) if url.tags else ()

        file_path = Path(
            self.config.output,
            *tag_path,
            url.username,
            str(url.created_at.year),
            f"{url.created_at.strftime('%B')}",
            f"[{url.created_at.year}-{url.created_at.month:02d}-{url.created_at.day:02d}] {file_id}{file_name.suffix}",
        )
        
        return file_path

    def handle_url(self, url: str, created_at: datetime) -> list[dict] | None:
        pass
    
    def sign_and_download(self, url: ExternalURL) -> list[DownloadResult] | None:
        self.sign(url)
        
        if not url.signed:
            return []
        
        file_path = self.get_file_path(url)
        downloaded = self.web.download(url, file_path)
        
        if not downloaded:
            return []
        
        if not isinstance(downloaded, DownloadResult):
            return []
                
        return [downloaded]
    
    def sign(self, url: ExternalURL) -> ExternalURL | None:
        pass
    
    def attempt_extraction(self, result: DownloadResult) -> list[DownloadResult] | None:
        results: list[DownloadResult] = []
        
        try:
            temp_path = Path(
                self.config.output,
                result.url.tags[0],
                result.url.username,
                "temp"
            )
            
            shutil.unpack_archive(
                str(result.path),
                str(temp_path)
            )
            
            result.path.unlink()
            
            # Rename extracted files
            for i, file in enumerate(temp_path.rglob("*"), start = 1):
                if file.is_file():
                    external_url = ExternalURL(
                        created_at = result.url.created_at,
                        url = result.url.url,
                        domain_name = result.url.domain_name,
                        username = result.url.username,
                        file_name = Path(file.name),
                        tags = result.url.tags
                    )
                    
                    new_name = self.get_file_path(external_url)
                    
                    file.rename(new_name)
                    
                    new_result = DownloadResult(
                        url = external_url,
                        path = new_name,
                        size = new_name.stat().st_size
                    )
                    
                    results.append(new_result)
        
        except shutil.ReadError:
            return None

        return results