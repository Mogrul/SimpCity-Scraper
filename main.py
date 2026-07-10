import logging

from src.shared.logger import load_logger
from src.core.core import Core

from src.core.session import Session
from src.core.site.goonbox import GoonBox

if __name__ == "__main__":
    load_logger()
    #core = Core()
    #core.scrape("https://simpcity.cr/threads/aiwa-aiwa_only-truegspot-yoursexylady18-aiwaonly.15084/")
    
    session = Session()
    #response = session.get("https://goonbox.cr/api/albums/LlOeu", "https://goonbox.cr/a/LlOeu")

    goonbox = GoonBox(
        url = "https://goonbox.cr/a/LlOeu",
        sites = {},
        session = session
    )
    goonbox.scrape()