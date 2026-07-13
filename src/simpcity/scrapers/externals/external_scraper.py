import logging
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from src.simpcity.models.external_scraper_data import ExternalScraperData
from src.http.models.download_request import HttpDownloadRequest
from src.http.models.download_response import HttpDownloadResponse
from src.http.http_client import HttpClient
from src.shared.config import Config

class ExternalScraper:
    def __init__(
            self,
            scraper_datas: list[ExternalScraperData],
            logger: logging.Logger | None = None
    ):
        self._logger = logger if logger else logging.getLogger("external.scraper")
        self._datas = scraper_datas
        self._config = Config()
        self._client = HttpClient()
    
    def scrape(self):
        pass
    
    def download(self, data: ExternalScraperData) -> HttpDownloadResponse:
        file_path = self._get_file_path(data)
        request = HttpDownloadRequest(
            url = data.url,
            destination = file_path
        )
        
        response = self._client.download(request)
        
        if response.success is True:
            size = 0 if not response.size else response.size
            time_taken = .0 if not response.time_taken else response.time_taken
            
            self._logger.info(
                f"{self._format_bytes(size):>10} "
                f"{self._format_duration(time_taken):>8} "
                f"Downloaded {file_path}"
            )
            
        else:
            self._logger.warning(
                f"{response.status_code}: Failed to download {data.url}"
            )
        
        return response
    
    def _get_file_path(self, data: ExternalScraperData):
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
                f"{file_id}"
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