from logging import Logger
from urllib.parse import urlparse
from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5
from typing import Any
from datetime import datetime

from src.core.session import Session
from src.core.util import get_domain_name
from src.core.enum.references import References

BASE_PATH = Path("Downloads")

class Site:
    def __init__(
            self,
            url: str,
            sites: dict[str, type[Site]],
            session: Session,
            logger: Logger,
            references: dict[str, Any] = {}
    ):
        self.url = url
        self.sites = sites
        self.logger = logger
        self.session = session
        self.references = references
        
        self.domain_name = get_domain_name(self.url)

    def scrape(self):
        self.logger.info(f"Attempting to scrape: {self.url}")
    
    def download_file(
            self,
            url: str,
            additional_references: dict = None
    ) -> tuple[str, Path]:
        file_path = self.build_file_path(url, additional_references)
        
        return self.session.download_file(url, file_path)
    
    def build_file_path(
            self,
            url: str,
            additional_references: dict = None
        ) -> Path:
        file = Path(urlparse(url).path)
        
        file_id = str(uuid5(NAMESPACE_DNS, file.name))[:8]
        
        if References.USERNAME in self.references:
            username: str = self.references[References.USERNAME]
            file_path = Path(
                BASE_PATH,
                username,
                file_id + file.suffix
            )
        
        else:
            file_path = Path(
                BASE_PATH,
                self.domain_name,
                file_id + file.suffix
            )
        
        if References.DATE in additional_references:
            file_parent = file_path.parent
            file_name = file_path.name
            date: datetime = additional_references[References.DATE]
            
            file_path = Path(
                file_parent,
                str(date.year),
                f"[{date.year}-{date.month:02d}-{date.day:02d}] " + file_name
            )
        
        elif References.DATE in self.references:
            file_parent = file_path.parent
            file_name = file_path.name
            date: datetime = self.references[References.DATE]
            
            file_path = Path(
                file_parent,
                str(date.year),
                f"[{date.year}-{date.month:02d}-{date.day:02d}] " + file_name
            )
        
        return file_path