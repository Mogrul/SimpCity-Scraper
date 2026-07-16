import json
import logging
import time
from http.cookiejar import MozillaCookieJar

import requests
from bs4 import BeautifulSoup

from config import Config
from enums import RequestType, ResponseType, StatusCode
from models import Request, Response, DownloadRequest, DownloadResponse


def _on_timeout(request: Request) -> Response:
    return Response(
        request = request,
        status_code = StatusCode.TIMEOUT
    )

def _on_error(request: Request, response: requests.Response) -> Response:
    return Response(
        request = request,
        status_code = StatusCode.FAILED
    )

class Session:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):
        if getattr(self, "_session", None):
            return

        self.session = requests.Session()
        self.logger = logging.getLogger("session")
        self.config = Config().network

        self.load_cookies()
        self.load_headers()

    def send(self, request: Request) -> Response:
        try:
            if request.request_type == RequestType.POST:
                response = self.session.post(
                    url = request.link,
                    params = request.params,
                )

            else:
                response = self.session.get(
                    url = request.link,
                    params = request.params
                )
        except TimeoutError:
            return _on_timeout(request)

        # Handle response
        if response.status_code != 200:
            return _on_error(request, response)

        try:
            # Send response as specified by type
            if request.response_type == ResponseType.SOUP:
                soup = BeautifulSoup(response.content, 'html.parser')

                return Response(
                    request = request,
                    status_code = StatusCode.SUCCESS,
                    data = soup
                )

            elif request.response_type == ResponseType.DICT:
                data = json.loads(response.text)

                return Response(
                    request = request,
                    status_code = StatusCode.SUCCESS,
                    data = data
                )

            else:
                return Response(
                    request = request,
                    status_code = StatusCode.SUCCESS,
                    data = response.text
                )

        except (ValueError, TypeError, json.decoder.JSONDecodeError):
            return _on_error(request, response)

    def download(self, request: DownloadRequest) -> DownloadResponse:
        # Handle download resuming
        temp_destination = request.destination.with_suffix(request.destination.suffix + ".temp")
        downloaded_bytes = 0
        headers = {}

        if temp_destination.exists():
            downloaded_bytes = temp_destination.stat().st_size

        if downloaded_bytes:
            headers["Range"] = f"bytes={downloaded_bytes}-"

        if request.headers:
            for key, value in request.headers.items():
                headers[key] = value

        request.destination.parent.mkdir(parents = True, exist_ok = True)
        start_time = time.perf_counter()

        with self.session.get(
            url = request.link,
            headers = headers,
            timeout = self.config.timeout,
            params = request.params
        ) as response:
            if response.status_code not in (200, 203):
                return DownloadResponse(status_code = StatusCode.FAILED, request = request)

            # Rejected range request
            if downloaded_bytes and response.status_code == 200:
                downloaded_bytes = 0
                temp_destination.unlink(missing_ok = True)

            mode = "ab" if downloaded_bytes else "wb"

            # Load the bytes into the temp file
            with open(temp_destination, mode) as f:
                for chunk in response.iter_content(self.config.chunk_size):
                    if chunk:
                        f.write(chunk)

        # Finalise the download on success
        time_taken = time.perf_counter() - start_time
        file_size = temp_destination.stat().st_size
        temp_destination.rename(request.destination)

        return DownloadResponse(
            status_code = StatusCode.SUCCESS,
            request = request,
            time_taken = time_taken,
            file_size = file_size,
        )

    def close(self):
        self.session.close()

    def load_cookies(self):
        cookie_path = self.config.cookies

        if not cookie_path.exists():
            return

        for file in cookie_path.iterdir():
            if not file.is_file():
                continue

            jar = MozillaCookieJar()
            jar.load(str(file), ignore_discard = True, ignore_expires = True)
            self.session.cookies.update(jar)

            self.logger.debug(f"Load cookies from {file}")

    def load_headers(self):
        self.session.headers.update(self.config.headers)