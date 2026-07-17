import logging

from domains import Domain
from enums import RequestType, ResponseType
from models import Post, Link, DownloadResponse, Request


class PixelDrain(Domain):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name = __class__.__name__,
            logger = logging.getLogger(__class__.__name__),
            *args,
            **kwargs
        )

    def on_submission(self, post: Post, link: Link) -> list[DownloadResponse]:
        responses = []

        if "/l/" in link.link:
            responses.extend(self.album(post, link))

        else:
            self.logger.critical(f"Unsupported link: {link.link}")

        return responses

    def album(self, post: Post, link: Link) -> list[DownloadResponse]:
        album_id = link.link.split("/")[-1]
        responses = []

        # Send API request to get album data
        request = Request(
            link = f"https://pixeldrain.com/api/list/{album_id}",
            request_type = RequestType.GET,
            response_type = ResponseType.DICT
        )
        response = self.session.send(request)

        if not isinstance(response.data, dict):
            return responses

        files = response.data.get("files", [])

        for file in files:
            filename = file.get("name")
            fileid = file.get("id")

            if (
                not isinstance(filename, str)
                or not isinstance(fileid, str)
            ):
                continue

            file_link = Link(
                post_id = link.post_id,
                link = link.link,
                domain = link.domain,
                signed = f"https://pixeldrain.com/api/file/{fileid}",
                filename = filename,
            )
            responses.append(self.file(post, file_link))

        return responses

    def file(self, post: Post, link: Link) -> DownloadResponse:
        return self.download(post, link)