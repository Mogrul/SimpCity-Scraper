import logging

from domains import Domain
from enums import RequestType, ResponseType
from models import Post, Link
from session import DownloadResponse, Request



class GoonBox(Domain):
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

        if "/img/" in link.link:
            return self.file(post, link)

        else:
            self.album(post, link)

        return None

    def album(self, post: Post, link: Link) -> list[DownloadResponse]:
        album_id = link.link.split("/a/")[-1]
        if "." in album_id:
            album_id = album_id.split(".")[-1]

        request = Request(
            link = f"https://goonbox.cr/api/albums/{album_id}/images",
            request_type = RequestType.GET,
            response_type = ResponseType.DICT,
            params = {
                "page": "1"
            }
        )
        response = self.session.send(request)

        if not isinstance(response.data, dict):
            return []

        pagination = response.data.get("pagination", {})
        last_page = pagination.get("last_page", 1)
        images = response.data.get("images", [])

        download_responses = []
        for page_num in range(1, last_page + 1):
            if self.stop_event.is_set(): break

            if page_num != 1:
                request = request
                request.params["page"] = str(page_num)
                response = self.session.send(request)
                if not isinstance(response.data, dict):
                    continue

                images = response.data.get("images", [])

            for image in images:
                filename = image.get("original_filename")
                signed = image.get("original_url")

                if (
                    not filename
                    or not signed
                ):
                    continue

                image_link = Link(
                    post_id = post.id,
                    link = link.link,
                    domain = link.domain,
                    signed = signed,
                    filename = filename,
                )

                # Add the files to the thread pool
                if self.executor:
                    future = self.executor.submit(
                        self.on_submission,
                        post,
                        image_link
                    )

                    with self.future_lock:
                        self.futures[future] = image_link

        return download_responses