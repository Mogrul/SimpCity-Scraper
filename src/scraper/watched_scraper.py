from bs4 import BeautifulSoup

from session import Session, Request, RequestType, ResponseType


class WatchedScraper:
    def __init__(self):
        self.session = Session()

    def get_watched(self) -> list[str]:
        # Visit watched page
        request = Request(
            link = "https://simpcity.cr/watched/threads",
            request_type = RequestType.GET,
            response_type = ResponseType.SOUP,
        )
        response = self.session.send(request)

        if not isinstance(response.data, BeautifulSoup):
            return []

        max_page_num = self.get_max_page_num(response.data)
        thread_links = []
        for page_num in range(1, max_page_num + 1):
            if page_num != 1:
                request.params["page"] = str(page_num)
                response = self.session.send(request)

            if not isinstance(response.data, BeautifulSoup):
                continue

            thread_links.extend(self.get_threads_in_page(response.data))

        return thread_links

    def get_max_page_num(self, page: BeautifulSoup) -> int:
        main_nav = page.find("ul", {"class": "pageNav-main"})
        if not main_nav: return 1

        navs = main_nav.find_all("li", {"class": "pageNav-page"})
        last_nav = navs[-1]  # Max page num

        try:
            return int(last_nav.get_text(strip=True))

        except ValueError:
            return 1

    def get_threads_in_page(self, page: BeautifulSoup) -> list[str]:
        titles = page.find_all("div", {"class": "structItem-title"})

        thread_links = []
        for title in titles:
            href = title.get("uix-href")
            if not isinstance(href, str):
                continue

            href = href.replace("/unread", "")
            thread_links.append(f"https://simpcity.cr{href}")

        return thread_links