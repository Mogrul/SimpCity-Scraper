import hashlib
import logging
import time

from domains import Domain
from enums import StatusCode, RequestType, ResponseType
from models import Post, Link, DownloadResponse, Request


class GoFile(Domain):
    def __init__(self, *args, **kwargs):
        super().__init__(
            name = __class__.__name__,
            logger = logging.getLogger(__class__.__name__),
            token_required = True,
            *args,
            **kwargs
        )

    def get_token(self) -> str:
        request = Request(
            link = f"https://api.gofile.io/accounts",
            request_type = RequestType.POST,
            response_type = ResponseType.DICT
        )
        response = self.session.send(request)

        if not isinstance(response.data, dict):
            return ""

        data = response.data.get("data", {})

        return data.get("token", "")

    def on_submission(self, post: Post, link: Link) -> list[DownloadResponse]:
        responses = []

        if "/d/" in link.link:
            return self.album(post, link)

        return responses

    def album(self, post: Post, link: Link) -> list[DownloadResponse]:
        responses = []
        album_id = link.link.split("/")[-1]

        request = Request(
            link = f"https://api.gofile.io/contents/{album_id}",
            request_type = RequestType.GET,
            response_type = ResponseType.DICT,
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Sec-Ch-Ua-Platform": "Windows",
                "x-bl": "en-GB",
                "Referer": "https://gofile.io/",
                "Origin": "https://gofile.io",
                "X-Website-Token": self.generate_website_token()
            }
        )
        response = self.session.send(request)

        if not isinstance(response.data, dict):
            return responses

        data = response.data.get("data", {})
        children = data.get("children", {})

        for file_id, file_data in children.items():
            filename = file_data.get("name")
            signed = file_data.get("link")

            if (
                not isinstance(filename, str)
                or not isinstance(signed, str)
            ):
                continue

            file_link = Link(
                post_id = link.post_id,
                link = link.link,
                domain = link.domain,
                signed = signed,
                filename = filename
            )

            responses.append(self.file(post, file_link))

        return responses

    def file(self, post: Post, link: Link) -> DownloadResponse:
        return self.download(
            post,
            link,
            headers = {
                "Cookie": f"accountToken={self.token}"
            }
        )

    def generate_website_token(self) -> str:
        user_agent = self.config.network.headers.get("User-Agent", str)
        timestamp = str(int(time.time() / 14400))
        language = "en-GB"
        token = self.token

        data =  (
            f"{user_agent}::"
            f"{language}::"
            f"{token}::"
            f"{timestamp}::"
            "9844d94d963d30"
        )

        return hashlib.sha256(data.encode()).hexdigest()