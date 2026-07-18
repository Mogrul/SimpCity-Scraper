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

    def on_submission(self, post: Post, link: Link) -> DownloadResponse | None:
        if self.stop_event.is_set():
            return None

        if link.signed:
            return self.file(post, link)

        elif "/l/" in link.link:
            self.album(post, link)

        else:
            self.logger.critical(f"Unsupported link: {link.link}")

        return None

    def album(self, post: Post, link: Link) -> None:
        album_id = link.link.split("/")[-1]

        # Send API request to get album data
        request = Request(
            link = f"https://pixeldrain.com/api/list/{album_id}",
            request_type = RequestType.GET,
            response_type = ResponseType.DICT
        )
        response = self.session.send(request)

        if not isinstance(response.data, dict):
            return None

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

            # Add the files to the thread pool
            if self.executor:
                future = self.executor.submit(
                    self.on_submission,
                    post,
                    file_link
                )

                with self.future_lock:
                    self.futures[future] = file_link

        return None