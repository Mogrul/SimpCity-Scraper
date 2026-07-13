import logging
from pathlib import Path
from http.cookiejar import MozillaCookieJar
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from src.shared.singleton_meta import SingletonMeta
from src.shared.config import Config
from .models.request import HttpRequest
from .models.response import HttpResponse

class HttpClient(metaclass = SingletonMeta):
    def __init__(self):
        self._logger = logging.getLogger("http.client")
        self._session = requests.session()
        self._notified_cookies: set[str] = set()
        self._config = Config()
        
        self._load_default_headers()
    
    def _load_cookies(self, request: HttpRequest):
        parsed = urlparse(request.url)
        domain = parsed.netloc
        
        if domain in self._notified_cookies:
            return
        
        cookie_path = Path(".cookies")
        cookie_file = Path(cookie_path, f"{domain}.txt")
        
        if not cookie_file.exists():
            self._logger.warning(f"Attempted to load cookie file {cookie_file} when it doesn't exist.")
            self._notified_cookies.add(domain)
            return
        
        jar = MozillaCookieJar()
        jar.load(
            str(cookie_file),
            ignore_discard = True,
            ignore_expires = True
        )
        
        self._logger.info(f"Loaded cookies from file {cookie_file}")
        self._session.cookies.update(jar)
        self._notified_cookies.add(domain)

    def _build_headers(self, request: HttpRequest) -> dict[str, str]:
        headers = {}
        
        if request.referer:
            headers["Referer"] = request.referer
        
        if request.origin:
            headers["Origin"] = request.origin
        
        return headers
    
    def _load_default_headers(self):
        headers = self._config.headers
        if not headers:
            return
        
        self._session.headers.update(headers)

    def get(self, request: HttpRequest) -> HttpResponse:
        self._load_cookies(request)
        headers = self._build_headers(request)
        
        response = self._session.get(
            url = request.url,
            headers = headers,
            timeout = self._config.timeout
        )
        
        self._logger.info(f"{response.status_code}: Sent GET request to {request.url}")
        
        return HttpResponse(
            request = request,
            status_code = response.status_code,
            headers = dict(response.headers),
            soup = (
                BeautifulSoup(response.text, "html.parser") if request.as_soup
                else None
            )
        )