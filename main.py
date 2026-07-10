import logging

from src.shared.logger import load_logger
from src.core.core import Core

from src.core.session import Session
from src.core.site.bunkr import Bunkr

if __name__ == "__main__":
    load_logger()
    core = Core()
    core.scrape("https://simpcity.cr/threads/aiwa-aiwa_only-truegspot-yoursexylady18-aiwaonly.15084/")