import logging

from domains import Domain
from models import Post, Link, DownloadResponse


class GoonBox(Domain):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name = __class__.__name__,
            logger = logging.getLogger(__class__.__name__),
            *args,
            **kwargs
        )

    def on_submission(self, post: Post, link: Link) -> list[DownloadResponse]:
        responses = []

        if "/img/" in link.link:
            responses.append(self.file(post, link))

        else:
            responses.extend(self.album(post, link))

        return responses

    def album(self, post: Post, link: Link) -> list[DownloadResponse]:
        return []

    def file(self, post: Post, link: Link) -> DownloadResponse:
        return self.download(post, link)