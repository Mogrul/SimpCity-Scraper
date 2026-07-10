from urllib.parse import urlparse
from pathlib import Path
import time
import logging

from bs4 import BeautifulSoup
from http.cookiejar import MozillaCookieJar
from undetected_chromedriver import Chrome, ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

class Session(Chrome):
    _instance = None
    
    def __new__(cls):
        if cls._instance == None:
            cls._instance = super().__new__(cls)

        return cls._instance
    
    def __init__(self):
        if getattr(self, "_initialised", False):
            return
        
        super().__init__(self._get_options())  
        
        self.visited_domains: list[str] = []
        self.logger = logging.getLogger("session")
        
        self._initialised = True
 
    def _get_options(self) -> ChromeOptions:
        options = ChromeOptions()
        
        return options
    
    def load_cookies(self, domain: str):        
        cookie_path = Path(".cookies", f"{domain}.txt")
        
        if not cookie_path.exists():
            return
        
        jar = MozillaCookieJar()
        jar.load(f".cookies/{domain}.txt", ignore_discard = True, ignore_expires = True)
        
        self.logger.info(f"Loading cookies for domain: {domain}")
        
        for cookie in jar:
            self.add_cookie({
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path
            })
    
    def get_from_file(self, file_path: str) -> BeautifulSoup | None:
        with open(file_path, "r", encoding = "utf-8") as f:
            data = f.read()
        
        return BeautifulSoup(data, "html.parser")
    
    def _get(self, url: str, sleep = 0):
        super().get(url)
        WebDriverWait(self, 10).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        time.sleep(sleep)
    
    def ensure_tab(self, tab_num: int):
        while len(self.window_handles) < tab_num:
            self.open_tabs(1)

        self.switch_to.window(self.window_handles[tab_num - 1])
    
    def get(self, url: str, sleep = 0, tab_num = 0) -> BeautifulSoup:
        self.ensure_tab(tab_num)
        
        parsed = urlparse(url)
        
        if parsed.hostname not in self.visited_domains:
            base_url = f"{parsed.scheme}://{parsed.hostname}/"
            self._get(base_url, sleep)
            
            self.load_cookies(parsed.hostname)
            self.visited_domains.append(parsed.hostname)
        
        self._get(url, sleep)

        self.logger.info(f"Visitted: {url}")
        
        return BeautifulSoup(
            self.page_source,
            "html.parser"
        )
    
    def scroll_to_bottom(self, sleep = 1):
        last_height = self.execute_script(
            "return document.body.scrollHeight"
        )

        while True:
            self.logger.info(f"Scrolling...")
            
            self.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            
            time.sleep(sleep)

            new_height = self.execute_script(
                "return document.body.scrollHeight"
            )

            if new_height == last_height:
                break

            last_height = new_height
    
    def open_tabs(self, tab_count=5):
        for _ in range(tab_count):
            old_count = len(self.window_handles)

            self.switch_to.new_window("tab")

            WebDriverWait(self, 10).until(
                lambda d: len(d.window_handles) > old_count
            )

            self.logger.info("Opened tab")
            
    def get_tab_source(self, tab_num: int) -> BeautifulSoup:
        self.switch_to.window(self.window_handles[tab_num])
        
        return BeautifulSoup(
            self.page_source,
            "html.parser"
        )
    
    def open_in_tab(self, url: str, tab_num: int):
        self.ensure_tab(tab_num)
        self._get(url)
    
    def cleanup_tabs(self):
        current = self.current_window_handle

        for handle in self.window_handles:
            if handle != current:
                self.switch_to.window(handle)
                self.close()

        self.switch_to.window(current)