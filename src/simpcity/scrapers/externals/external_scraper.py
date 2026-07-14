import logging
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.simpcity.models.external_scraper_data import ExternalScraperData
from src.http.models import (
    HttpDownloadResponse,
    HttpDownloadRequest
)
from src.http.http_client import HttpClient
from src.shared import Config

class ExternalScraper:
    def __init__(
            self,
            scraper_datas: list[ExternalScraperData],
            thread_prefix: str | None = None,
            logger: logging.Logger | None = None
    ):
        self._logger = logger if logger else logging.getLogger("external.scraper")
        self._thread_prefix = thread_prefix if thread_prefix else "external.scraper.thread"
        self._datas = scraper_datas
        self._config = Config()
        self._client = HttpClient()
    
    def scrape(self) -> tuple[int, int, int, int]:
        downloaded = 0
        failed = 0
        total = 0
        exists = 0
        
        with ThreadPoolExecutor(
                max_workers = self._config.workers,
                thread_name_prefix = self._thread_prefix
        ) as executor:
            futures = [
                executor.submit(self.on_scrape, data)
                for data in self._datas
            ]
            
            for future in as_completed(futures):
                try:
                    responses = future.result()
                
                except Exception as e:
                    self._logger.exception(f"Error on scrape: {e}")
                    continue
                
                if not responses:
                    failed += 1
                    total += 1
                    continue
                
                if not isinstance(responses, tuple):
                    failed += 1
                    total += 1
                    continue
                
                for response in responses:
                    if response.success is True:
                        size = 0 if not response.size else response.size
                        time_taken = .0 if not response.time_taken else response.time_taken
                        
                        self._logger.info(
                            f"{self._format_bytes(size):>10} "
                            f"{self._format_duration(time_taken):^8} "
                            f"      Downloaded {response.request.destination}"
                        )
                        
                        downloaded += 1
                        
                    else:
                        if not response.is_duplicate:
                            self._logger.warning(
                                f"{response.status_code}: Failed to download {response.request.url}"
                            )
                            failed += 1
                        
                        else:
                            exists += 1
                    
                    total += 1
                
        return (
            downloaded,
            failed,
            total,
            exists
        )
    
    def on_scrape(
        self,
        data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse] | None:
        pass
    
    def download(self, data: ExternalScraperData) -> HttpDownloadResponse:
        file_path = self._get_file_path(data)

        return self._client.download(HttpDownloadRequest(
            url = data.url,
            destination = file_path
        ))
    
    def _handle_album(
            self,
            data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse] | None:
        return None
    
    def _handle_file(
            self,
            data: ExternalScraperData
    ) -> tuple[HttpDownloadResponse] | None:
        return None
    
    def _get_file_path(self, data: ExternalScraperData):
        url = data.url.split("/")[-1]
        
        if "?" in data.url:
            url = url.split("?")[0]
        
        if data.file_name:
            id = str(uuid5(NAMESPACE_URL, url + data.file_name))
            ext_name = Path(data.file_name)
        
        else:
            id = str(uuid5(NAMESPACE_URL, url))
            ext_name = Path(url)
        
        if data.file_name:
            ext_name = Path(data.file_name)
            file_id = str(
                uuid5(NAMESPACE_URL, data.url + data.file_name)
            ).replace("-", "")[:-16]
        
        else:
            ext_name = Path(data.url.split("/")[-1])
            file_id = str(
                uuid5(NAMESPACE_URL, data.url)
            ).replace("-", "")[:-16]
        
        tag_path = (data.tags[0],) if data.tags else ()
        
        return Path(
            self._config.download_location,
            *tag_path,
            data.username,
            str(data.posted_at.year),
            str(data.posted_at.strftime("%B")),
            (
                "["
                f"{data.posted_at.year}-"
                f"{data.posted_at.month:02d}-"
                f"{data.posted_at.day:02d}"
                "] "
                f"{id}"
                f"{ext_name.suffix}"
            )
        ) # Downloads/OnlyFans/InsaneBirkin/2026/04/[2026-04-21] 821jddh.jpg
    
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