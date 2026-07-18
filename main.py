import logging

from config import Config
from database import Database
from shared.logger import load_logger
from scraper import Scraper
from session import Session

config = Config()
config.load_config()

logger = load_logger()

if config.debug:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

if config.database.enabled:
    database = Database()

session = Session()

scraper = Scraper()
scraper.run()