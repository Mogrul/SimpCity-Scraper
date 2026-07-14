import os
import logging
from pathlib import Path

from src.shared import load_logger, Config
from src.simpcity.simpcity import SimpCity

def check_paths():
    logger = logging.getLogger("integrity")
    
    # Config file
    c = Config()
    if not c.exists():
        c.generate()
        logger.critical(f"No config.json found - edit the newly generated one and restart the program.")
        os._exit(0)
    
    # Cookies path
    cookie_path = Path(".cookies")
    if not cookie_path.exists():
        cookie_path.mkdir(parents = True, exist_ok = True)
        logger.critical(f"No .cookies folder found, add your netscape simpcity.txt cookies to the newly generated folder and restart the program.")
        os._exit(0)

if __name__ == "__main__":
    logger = load_logger()
    check_paths()
    
    c = Config()
    success = c.load_json()
    
    if not success:
        logger.critical("Failed to read config, exiting...")
        os._exit(0)
    
    ss = SimpCity()
    ss.scrape("https://simpcity.cr/threads/insanebirkin.1761775")