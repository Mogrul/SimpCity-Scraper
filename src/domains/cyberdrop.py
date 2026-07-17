import logging

from domains import Domain
from enums import ResponseType, RequestType, StatusCode
from models import Post, Link, DownloadResponse, Request


class CyberDrop(Domain):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name = __class__.__name__,
            logger = logging.getLogger(__class__.__name__),
            *args,
            **kwargs
        )

    def on_submission(self, post: Post, link: Link) -> list[DownloadResponse]:
        responses = []

        if "/e/" in link.link:
            responses.append(self.file(post, link))

        return responses

    def file(self, post: Post, link: Link) -> DownloadResponse:
        file_id = link.link.split("/")[-1]

        # Get file info
        request = Request(
            link=f"https://api.cyberdrop.cr/api/file/info/{file_id}",
            request_type=RequestType.GET,
            response_type=ResponseType.DICT,
        )
        response = self.session.send(request)

        if not isinstance(response.data, dict):
            return DownloadResponse(status_code = StatusCode.FAILED)

        filename = response.data.get("name")

        if not filename:
            return DownloadResponse(status_code = StatusCode.FAILED)

        # Get download link
        request = Request(
            link = f"https://api.cyberdrop.cr/api/file/auth/{file_id}",
            request_type = RequestType.GET,
            response_type = ResponseType.DICT,
        )
        response = self.session.send(request)

        if not isinstance(response.data, dict):
            return DownloadResponse(status_code = StatusCode.FAILED)

        signed = response.data.get("url")

        if not signed:
            return DownloadResponse(status_code = StatusCode.FAILED)

        link.filename = filename
        link.signed = signed

        return self.download(post, link)