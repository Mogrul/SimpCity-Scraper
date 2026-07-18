import base64
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup, Tag

from scraper import Link, Post


class PostScraper:
    def __init__(self, page: BeautifulSoup):
        self.page = page

    def scrape(self) -> tuple[dict[int, Post], list[Link]]:
        posts = {}
        links = []

        cells = self.get_cells()
        for cell in cells:
            post = self.get_post_in_cell(cell)
            if not post: continue

            posts[post.id] = post
            links.extend(self.get_links_in_cell(post.id, cell))

        return posts, links

    def get_cells(self) -> list[Tag]:
        cells = self.page.find_all("div", {"class": "message-cell--main"})
        cells = cells[:-1]

        return cells

    def get_post_in_cell(self, cell: Tag) -> Post | None:
        # Retrieve the ID
        user_content = cell.find("div", {"class": "message-userContent"})
        if not user_content: return None

        post_id_str = user_content.get("data-lb-id")
        if not isinstance(post_id_str, str): return None
        id_str = post_id_str.split("-")[-1]

        try:
            id = int(id_str)

        except ValueError:
            return None

        # Retrieve posted at
        time = cell.find("time", {"class": "u-dt"})
        if not time: return None
        timestamp_str = time.get("data-timestamp")
        if not isinstance(timestamp_str, str): return None

        try:
            timestamp = int(timestamp_str)

        except ValueError:
            return None

        date = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        return Post(id, date)

    def get_links_in_cell(self, post_id: int, cell: Tag) -> list[Link]:
        links = []

        # Handle external links first
        external_links = cell.find_all("a", {"class": "link--external"})

        for external_link in external_links:
            href = external_link.get("href")
            if not isinstance(href, str): continue
            parsed = urlparse(href)
            domain = parsed.netloc

            signed = None
            if "goonbox.cr" in href and "/img/" in href:
                # Get goonbox signed URL
                img = external_link.find("img")
                if not img: continue
                signed = img.get("src")
                if not isinstance(signed, str): continue
                signed = signed.replace(".md", "")

            # Decode redirects if present (base64)
            if "/redirect/" in href:
                encoded = parse_qs(parsed.query)["to"][0]
                decoded = base64.urlsafe_b64decode(
                    encoded + "=" * (-len(encoded) % 4)
                ).decode("utf-8")
                href = decoded
                parsed = urlparse(href)
                domain = parsed.netloc

            links.append(Link(post_id, href, domain, signed))

        # Handle embeds
        embeds = cell.find_all("iframe", {"class": "saint-iframe"})

        for embed in embeds:
            src = embed.get("src")
            if not isinstance(src, str): continue
            parsed = urlparse(src)
            domain = parsed.netloc

            signed = None
            if "turbo.cr" in src and "/embed/" in src:
                src = src.replace("/embed/", "/v/")

            links.append(Link(post_id, src, domain, signed))

        return links