import logging
from http.cookiejar import MozillaCookieJar
from pathlib import Path
import json
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

from .util import get_domain_name
from .models import DownloadResult, ExternalURL

from src.shared.config import Config

class Web(requests.Session):
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        
        return cls._instance
    
    def __init__(self):
        if getattr(self, "_initialised", False):
            return
        
        super().__init__()
        self.logger = logging.getLogger("web")
        self.parsed_cookies: set[str] = set()
        self.config = Config()
        
        self.load_headers()
        self.load_adapter()
        
        self._initialised = True
    
    def load_cookie(
            self,
            cookie_path = ".cookies",
            domain_name = "simpcity.cr"
    ):
        file_path = Path(cookie_path, f"{domain_name}.txt")
        self.parsed_cookies.add(domain_name)
        
        if not file_path.exists():
            self.logger.warning(f"Attempted to load cookie that doesn't exist: {domain_name}.txt")
            return
        
        jar = MozillaCookieJar()
        jar.load(str(file_path), ignore_discard = True, ignore_expires = True)
        
        self.logger.info(f"Loaded cookies for {domain_name}")
        self.cookies.update(jar)
  
    def load_adapter(self):
        adapter = HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100
        )
        
        self.mount("http://", adapter)
        self.mount("https://", adapter)
    
    def load_headers(self):
        self.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/138.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        })
    
    def build_headers(
            self,
            url: str,
            referer: str | None = None,
            origin: str | None = None,
            load_cookies = True
    ) -> dict:
        domain_name = get_domain_name(url)
        
        if load_cookies:
            if domain_name not in self.parsed_cookies:
                self.load_cookie(domain_name = domain_name)
        
        headers = {}
        
        if referer:
            headers["Referer"] = referer
        
        if origin:
            headers["Origin"] = origin
        
        return headers

    def post(
            self,
            url: str,
            payload: dict,
            referer: str | None = None,
            origin: str | None = None,
    ) -> dict | None:
        headers = self.build_headers(url, referer, origin)
        headers["Content-Type"] = "application/json"
        
        reply = super().post(
            url,
            json = payload,
            headers = headers,
            timeout = self.config.timeout
        )
        
        self.logger.info(f"Sent POST request: {url}")
        
        try:
            return reply.json()

        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode reply to json from {url}")
            return None

    def get(
            self,
            url: str,
            referer: str | None = None,
            origin: str | None = None,
            params: dict | None = None,
            return_dict = False,
            return_headers = False,
            log = True
    ) -> BeautifulSoup | dict | dict | None:
        headers = self.build_headers(url, referer, origin)
        
        reply = super().get(
            url,
            headers = headers,
            timeout = self.config.timeout,
            params = params
        )
        
        if reply.status_code != 200:
            self.logger.error(f"Failed with status {reply.status_code} for {url}")
            return None
        
        if log:
            self.logger.info(f"Sent GET request: {url}")
        
        if return_headers:
            return dict(reply.headers)
        
        if return_dict:
            try:
                return reply.json()
            
            except json.JSONDecodeError:
                self.logger.error(f"Failed to decode reply to json from {url}")
                return None
        
        return BeautifulSoup(reply.content, "html.parser")

    def get_cookies(
            self,
            url: str,
            referer: str
    ) -> dict | None:
        domain_name = get_domain_name(url)
        parsed = urlparse(url)
        
        if (
                not parsed
                or not parsed.hostname
        ):
            self.logger.error(f"Failed to parse URL {url}")
            return None
        
        if domain_name in self.parsed_cookies:
            return self.cookies.get_dict(
                domain = "." + parsed.hostname
            )
        
        headers = self.build_headers(url, referer, load_cookies = False)
        
        reply = super().get(
            url,
            headers = headers,
            timeout = self.config.timeout
        )
        
        self.logger.info(f"Sent API request to: {url}")
        
        if reply.status_code != 200:
            self.logger.error(f"Failed with status: {reply.status_code} for {url}")
            return None
        
        # Attempt to get cookies back
        grabbed_cookies = self.cookies.get_dict(domain = "." + parsed.hostname)
        
        if not grabbed_cookies:
            self.logger.error(f"Failed to get cookies after successful request")
            return None
        
        self.parsed_cookies.add(domain_name)
        
        return grabbed_cookies

    def download(
        self,
        url: ExternalURL,
        destination: Path,
        referer: str | None = None,
        origin: str | None = None,
        params: dict | None = None
    ) -> DownloadResult | None:
        if destination.exists():
            return
        
        headers = self.build_headers(url.url, referer, origin)
        
        destination.parent.mkdir(parents = True, exist_ok = True)
        temp_path = destination.with_suffix(destination.suffix + ".temp")
        
        downloaded = 0
        if temp_path.exists():
            downloaded = temp_path.stat().st_size
        
        if downloaded:
            headers["Range"] = f"bytes={downloaded}"
        
        with super().get(
            url = url.signed if url.signed else url.url,
            headers = headers,
            params = params,
            timeout = self.config.timeout
        ) as response:
            # Server ignored Range request, restart download
            if downloaded and response.status_code == 200:
                downloaded = 0
                temp_path.unlink()
            
            if response.status_code not in (200, 203):
                return
            
            mode = "ab" if downloaded else "wb"
            
            with open(temp_path, mode) as file:
                for chunk in response.iter_content(self.config.chunk_size):
                    if chunk:
                        file.write(chunk)
            
        temp_path.rename(destination)
        
        return DownloadResult(
            url = url,
            path = destination,
            size = destination.stat().st_size
        )