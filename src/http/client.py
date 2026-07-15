from dataclasses import asdict
from http.cookiejar import MozillaCookieJar
import logging
from pathlib import Path
import time
import json

import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
import brotli

from src.shared import SingletonMeta, Config
from .models import HTTPRequest, HTTPResponse, HTTPHeaders
from .enums import RequestType, ResponseType

class HTTPClient(metaclass = SingletonMeta):
    def __init__(self):
        self._logger = logging.getLogger("http.client")
        self._session = requests.session()
        self._config = Config()
        
        self._loaded_cookies: set[str] = set()
        
        self._load_adapter()
        self._load_headers()
        self._load_cookies()
    
    # Sending request and handling their responses
    def send(self, request: HTTPRequest) -> HTTPResponse:
        # Goonbox cookie hook
        if "goonbox.cr" not in self._loaded_cookies:
            self._session.get(url = "https://goonbox.cr/api/auth/me")
            self._loaded_cookies.add("goonbox.cr")
        
        # Send the request
        if request.request_type == RequestType.GET:
            try:
                response = self._session.get(
                    url = request.url,
                    timeout = self._config.timeout,
                    params = request.params
                )
            
            except TimeoutError:
                return self._on_timeout(request)
        
        elif request.request_type == RequestType.DOWNLOAD:
            return self._on_download(request)
        
        else:
            try:
                response = self._session.post(
                    url = request.url,
                    json = request.payload,
                    params = request.params
                )
            
            except TimeoutError:
                return self._on_timeout(request)
        
        # Handle status codes
        if response.status_code != 200:
            return self._on_error(request, response)
        
        self._logger.info(f"{response.status_code}: Sent request to: {response.url}")
        
        match request.response_type:
            case ResponseType.TEXT:
                return self._on_text(request, response)
            
            case ResponseType.SOUP:
                return self._on_soup(request, response)
            
            case ResponseType.DICT:
                return self._on_dict(request, response)
            
            case ResponseType.HEADERS:
                return self._on_headers(request, response)
            
            case _:
                return self._on_error(request, response)
    
    def _get_headers(self, headers: HTTPHeaders) -> dict:
        new_headers = asdict(headers)
        default_headers = dict(self._session.headers)
        
        for key, value in new_headers:
            if not value:
                continue
            default_headers[key] = value
        
        return default_headers
    
    def _on_timeout(self, request: HTTPRequest) -> HTTPResponse:
        self._logger.error(f"408: Timeout on {request.url}")
        return HTTPResponse(
            request,
            status_code = 408
        )
    
    def _on_error(self, request: HTTPRequest, response: requests.Response) -> HTTPResponse:
        self._logger.error(f"{response.status_code}: Error from {response.url}")
        
        return HTTPResponse(
            request,
            status_code = response.status_code,
            data = response.text,
            headers = dict(response.headers)
        )
    
    def _on_unresponsive_error(self, request: HTTPRequest) -> HTTPResponse:
        return HTTPResponse(
            request = request,
            status_code = 404
        )
    
    def _on_headers(self, request: HTTPRequest, response: requests.Response) -> HTTPResponse:
        return HTTPResponse(
            request = request,
            status_code = response.status_code,
            data = dict(response.headers)
        )
    
    def _on_text(self, request: HTTPRequest, response: requests.Response) -> HTTPResponse:
        return HTTPResponse(
            request,
            status_code = response.status_code,
            data = response.text
        )
    
    def _on_soup(self, request: HTTPRequest, response: requests.Response) -> HTTPResponse:
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            
        except TypeError:
            return self._on_error(request, response)
        
        return HTTPResponse(
            request = request,
            status_code = response.status_code,
            data = soup
        )
    
    def _on_dict(self, request: HTTPRequest, response: requests.Response) -> HTTPResponse:
        try:
            data = response.json()

        except ValueError:
            # Try and uncompress br format
            try:
                data = json.loads(
                    brotli.decompress(response.content)
                )
            
            except (ValueError, brotli.error):
                return self._on_error(request, response)
        
        return HTTPResponse(
            request = request,
            status_code = response.status_code,
            data = data
        )
    
    def _on_download(self, request: HTTPRequest) -> HTTPResponse:
        if not isinstance(request.payload, dict):
            self._logger.critical(f"Failed to extract payload on download request: {request}")
            return self._on_unresponsive_error(request)
        
        destination = request.payload.get("destination")
        
        if not isinstance(destination, Path):
            return self._on_unresponsive_error(request)
        
        # If it exists
        if destination.exists():
            return HTTPResponse(
                request = request,
                status_code = 409
            )
        
        chunk_size = self._config.chunk_size
        
        # Handle resuming
        temp_destination = destination.with_suffix(destination.suffix + ".temp")
        
        downloaded_bytes = 0
        headers = {}
        if temp_destination.exists():
            downloaded_bytes = temp_destination.stat().st_size
        
        if downloaded_bytes:
            headers["Range"] = f"bytes={downloaded_bytes}"
        
        if request.headers:
            for key, value in request.headers.items():
                headers[key] = value
        
        # Create the parent directory
        destination.parent.mkdir(parents = True, exist_ok = True)
        
        start_time = time.perf_counter()
        with self._session.get(
                url = request.url,
                headers = headers,
                timeout = self._config.timeout,
                params = request.params
        ) as response:
            
            # Rejected resume request
            if downloaded_bytes and response.status_code == 200:
                downloaded_bytes = 0
                temp_destination.unlink()
            
            # Handle failure
            if response.status_code not in (200, 203):
                return self._on_error(request, response)
            
            mode = "ab" if downloaded_bytes else "wb"
            
            # Load the bytes into the file
            with open(temp_destination, mode) as file:
                for chunk in response.iter_content(chunk_size):
                    if chunk:
                        file.write(chunk)
        
        # Rename temp file to destination of success
        file_size = temp_destination.stat().st_size
        temp_destination.rename(destination)
        time_taken = time.perf_counter() - start_time
        
        return HTTPResponse(
            request = request,
            status_code = response.status_code,
            data = {
                "destination": destination,
                "file_size": file_size,
                "time_taken": time_taken
            }
        )
    
    # Loading functions
    def _load_cookies(self):
        """Loads all the cookie text files in a cookie path.

        Args:
            cookie_path (Path): The path to scan for immediate text files.
        """
        cookie_path = self._config.cookie_path
        
        if not cookie_path.exists():
            self._logger.error(f"Failed to locate {cookie_path}")
            return None
        
        for file in cookie_path.iterdir():
            if not file.is_file():
                continue
            
            jar = MozillaCookieJar()
            jar.load(str(file), ignore_discard = True, ignore_expires = True)
            self._session.cookies.update(jar)
            
            self._logger.info(f"Added cookies from {file}")
    
    def _load_adapter(self):
        """Loads an adapter into the session for concurrent connections."""
        adapter = HTTPAdapter(
            pool_connections = 100,
            pool_maxsize = 100
        )
        
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
    
    def _load_headers(self):
        headers = self._config.headers
        if not headers:
            return
        
        self._session.headers.update(headers)