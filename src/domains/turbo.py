import logging

from domains import Domain
from enums import RequestType, ResponseType, StatusCode
from models import Post, Link, DownloadResponse, Request


class Turbo(Domain):
    def __init__(self, *args, **kwargs):
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

        else:
            self.logger.critical(link.link)

        return responses

    def file(self, post: Post, link: Link) -> DownloadResponse:
        file_id = link.link.split("/v/")[-1]

        request = Request(
            link = f"https://turbo.cr/api/sign",
            request_type = RequestType.GET,
            response_type = ResponseType.DICT,
            params = {
                "v": file_id
            }
        )
        response = self.session.send(request)

        if not isinstance(response.data, dict):
            return DownloadResponse(status_code = StatusCode.FAILED)

        file_name = response.data.get("filename")
        signed = response.data.get("url")

        if (
            not file_name
            or not signed
        ): return DownloadResponse(status_code = StatusCode.FAILED)

        link.signed = signed
        link.filename = file_name

        return self.download(post, link)