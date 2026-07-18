import logging
from urllib.parse import unquote

from bs4 import BeautifulSoup

from scraper import Thread

class ThreadScraper:
    def __init__(self, page: BeautifulSoup, link: str) -> None:
        self.logger = logging.getLogger("scraper.thread")
        self.page = page
        self.link = link

    def scrape(self) -> Thread | None:
        max_page_num = self.get_max_page_num()
        id = self.get_id()
        username = self.get_username()
        tags = self.get_tags()

        if (
            not id
            or not username
            or not tags
        ):
            return None

        return Thread(
            id = id,
            username = username,
            tags = tags,
            max_page_num = max_page_num,
        )

    def get_max_page_num(self) -> int:
        main_nav = self.page.find("ul", {"class": "pageNav-main"})
        if not main_nav: return 1

        navs = main_nav.find_all("li", {"class": "pageNav-page"})
        last_nav = navs[-1]  # Max page num

        try:
            return int(last_nav.get_text(strip=True))

        except ValueError:
            return 1

    def get_id(self) -> int | None:
        id_str = self.link.split(".")[-1]

        try:
            return int(id_str)

        except ValueError:
            return None

    def get_username(self) -> str:
        usr = self.link.split("/")[-1].split(".")[0]
        items = usr.split("-")
        titled = [item.title() for item in items[:2]]

        return unquote(" ".join(titled).strip())

    def get_tags(self) -> list[str]:
        labels = self.page.find_all("span", {"class": "label"})
        texts: list[str] = []

        for label in labels:
            text = label.get_text(strip = True)
            texts.append(text)

        return texts