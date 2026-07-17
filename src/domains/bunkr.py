import logging

from bs4 import BeautifulSoup

from domains import Domain
from enums import RequestType, ResponseType, StatusCode
from models import Post, Link, DownloadResponse, Request


class Bunkr(Domain):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            name = __class__.__name__,
            logger = logging.getLogger(__class__.__name__),
            *args,
            **kwargs
        )

    def on_submission(self, post: Post, link: Link) -> list[DownloadResponse]:
        responses = []
        if self.stop_event.is_set(): return responses

        if "/v/" in link.link:
            responses.append(self.file(post, link))

        elif "/f/" in link.link:
            responses.append(self.file(post, link))

        elif "/a/" in link.link:
            responses.extend(self.album(post, link))

        else:
            self.logger.critical(f"Unsupported link: {link.link}")

        return responses

    def album(self, post: Post, link: Link) -> list[DownloadResponse]:
        def get_max_page_num(soup: BeautifulSoup) -> int:
            pagination = soup.find("nav", {"class": "pagination"})
            if not pagination: return 1
            hrefs = pagination.find_all("a")
            if not hrefs: return 1

            top_href = hrefs[-2]
            try:
                return int(top_href.get_text())

            except ValueError:
                return 1

        responses = []

        # Visit first page
        request = Request(
            link = link.link,
            request_type = RequestType.GET,
            response_type = ResponseType.SOUP
        )
        response = self.session.send(request)

        if not isinstance(response.data, BeautifulSoup):
            return responses

        max_page_num = get_max_page_num(response.data)

        for page_num in range(1, max_page_num + 1):
            if self.stop_event.is_set(): return responses
            if page_num != 1:
                request.params["page"] = str(page_num)
                response = self.session.send(request)

            if not isinstance(response.data, BeautifulSoup):
                continue

            # Extract items from page
            items = response.data.find_all("div", {"class": "theItem"})
            for item in items:
                href = item.get("href")
                if not isinstance(href, str): continue
                href = "https://bunkr.cr" + href
                new_link = Link(
                    post_id = link.post_id,
                    link = href,
                    domain = link.domain
                )

                responses.append(self.file(post, new_link))

        return responses

    def file(self, post: Post, link: Link) -> DownloadResponse:
        if self.stop_event.is_set(): return DownloadResponse(status_code = StatusCode.FAILED)
        link.link = link.link.replace("/v/", "/f/")

        # Visit site to get file ID
        request = Request(
            link = link.link,
            request_type = RequestType.GET,
            response_type = ResponseType.SOUP
        )
        response = self.session.send(request)

        if not isinstance(response.data, BeautifulSoup):
            return DownloadResponse(status_code = StatusCode.FAILED)

        script = response.data.find("script", {"src": "../js/lv.js"})
        if not script: return DownloadResponse(status_code = StatusCode.FAILED)
        file_id = script.get("data-file-id")

        if not isinstance(file_id, str):
            return DownloadResponse(status_code = StatusCode.FAILED)

        # Get the path, name and domain using the file id
        request = Request(
            link = f"https://dl.bunkr.cr/api/_001_v2",
            request_type = RequestType.POST,
            response_type = ResponseType.DICT,
            payload = {
                "id": file_id
            }
        )
        response = self.session.send(request)

        if not isinstance(response.data, dict):
            return DownloadResponse(status_code = StatusCode.FAILED)

        filename = response.data.get("original")
        link.filename = filename
        api_domain = response.data.get("mediafiles")
        api_path = response.data.get("path")

        if (
            not isinstance(filename, str)
            or not isinstance(api_domain, str)
            or not isinstance(api_path, str)
        ):
            return DownloadResponse(status_code = StatusCode.FAILED)

        # Sign the path to get token and ex for downloading
        request = Request(
            link = f"https://glb-apisign.cdn.cr/sign",
            request_type = RequestType.GET,
            response_type = ResponseType.DICT,
            params = {
                "path": api_path
            }
        )
        response = self.session.send(request)

        if not isinstance(response.data, dict):
            return DownloadResponse(status_code = StatusCode.FAILED)

        ex = response.data.get("ex")
        token = response.data.get("token")

        if (
            not isinstance(ex, int)
            or not isinstance(token, str)
        ):
            return DownloadResponse(status_code = StatusCode.FAILED)

        # Construct the signed URL
        link.signed = api_domain + api_path

        return self.download(
            post,
            link,
            params = {
                "n": filename,
                "token": token,
                "ex": str(ex),
            }
        )