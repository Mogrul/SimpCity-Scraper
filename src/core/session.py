import logging
import requests
from pathlib import Path
from http.cookiejar import MozillaCookieJar
import json
import time

from bs4 import BeautifulSoup

from .util import get_domain_name

class Session(requests.Session):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("requests")
        self.loaded_cookies: set[str] = set()
        
        self.load_headers()
    
    def load_cookies(
            self,
            cookies_path = ".cookies",
            domain_name = "simpcity"
    ):
        file_path = Path(cookies_path, domain_name + ".txt")
        if not file_path.exists():
            self.logger.warning(f"Cookie file not found: {file_path}")
            return

        jar = MozillaCookieJar()
        jar.load(file_path, ignore_discard = True, ignore_expires = True)

        self.logger.info(f"Loaded cookies: {file_path}")
        
        self.cookies.update(jar)
    
    def load_headers(self):
        self.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/138.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        })
    
    def build_request(
            self,
            url: str,
            referer: str = None,
            origin: str = None
    ) -> dict:
        # Load cookies if not loaded for domain
        domain_name = get_domain_name(url)
        if domain_name not in self.loaded_cookies:
            self.load_cookies(domain_name = domain_name)
            self.loaded_cookies.add(domain_name)
            
        # Add headers if specified
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
            referer: str = None,
            origin: str = None,
            timeout = 30
    ) -> dict:
        headers = self.build_request(url, referer, origin)
        headers["Content-Type"] = "application/json"
        headers["Accept-Encoding"] = "gzip, deflate, br, zstd"
        
        reply = super().post(url, json = payload)
        
        if reply.status_code == 200:
            self.logger.info(f"Successful reply from {url}")
            
            try:
                return reply.json()

            except json.JSONDecodeError:
                self.logger.error(f"Failed to get JSON from {url}")
                return None
        
        else:
            self.logger.warning(f"Failed reply from {url} with status {reply.status_code}")
            return None
    
    def get_json(
            self,
            url: str,
            referer: str = None,
            params: dict = None,
            timeout = 30
    ) -> dict:
        headers = self.build_request(url, referer)
        
        # Commit request to url
        if params:
            reply = super().get(
                url,
                headers = headers,
                timeout = timeout,
                params = params
            )
            
        else:
            reply = super().get(
                url,
                headers = headers,
                timeout = timeout
            )
        
        if reply.status_code == 200:
            self.logger.info(f"Successful reply from {url}")
            
            try:
                return reply.json()

            except json.JSONDecodeError:
                self.logger.error(f"Failed to get JSON from {url}")
                return None
        
        else:
            self.logger.warning(f"Failed reply from {url} with status {reply.status_code}")
            return None

    def get(
            self,
            url: str,
            referer: str = None,
            timeout = 30
    ) -> BeautifulSoup | None:
        headers = self.build_request(url, referer)
        
        # Commit request to url
        reply = super().get(
            url,
            headers = headers,
            timeout = timeout
        )
        
        if reply.status_code == 200:
            self.logger.info(f"Successful reply from {url}")
            soup = BeautifulSoup(reply.content, "html.parser")
            return soup
        
        else:
            self.logger.warning(f"Failed reply from {url} with status {reply.status_code}")
            return None
    
    def download_file(
            self,
            url: str,
            destination: Path
    ) -> tuple[str, Path]:
        if destination.exists():
            return (url, destination)
        
        temp_path = destination.with_name(destination.name + ".temp")
        downloaded = temp_path.stat().st_size if temp_path.exists() else 0
        
        headers = {}
        if downloaded:
            headers["Range"] = f"bytes={downloaded}"
        
        headers["Referer"] = url
        
        # Create temp path base paths
        temp_path.parent.mkdir(parents = True, exist_ok = True)
        
        start = time.time()
        downloaded_now = downloaded
        with super().get(url, headers = headers, stream = True) as response:
            # Server ignored Range request, restart download
            if downloaded and response.status_code == 200:
                downloaded = 0
                temp_path.unlink()
            
            if response.status_code not in (200, 203):
                return
                
            mode = "ab" if downloaded else "wb"
            
            with open(temp_path, mode) as file:
                for chunk in response.iter_content(chunk_size = 1024 * 1024):
                    if chunk:
                        file.write(chunk)
                    
                        downloaded_now += len(chunk)

                        if downloaded_now // (10 * 1024 * 1024) > downloaded // (10 * 1024 * 1024):
                            elapsed = time.time() - start
                            speed = downloaded_now / elapsed / (1024 * 1024)
                            self.logger.info(f"Downloaded {downloaded_now / (1024*1024):.1f} MB ({speed:.2f} MB/s)")
                    
        temp_path.rename(destination)
        self.logger.info(f"Downloaded {url} -> {destination}")
        return (url, destination)
        