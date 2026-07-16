import logging

from config import Config
from logger import load_logger
from scraper import Scraper
from session import Session

logger = load_logger()
logger.setLevel(logging.DEBUG)

config = Config()
config.load_config()
session = Session()
scraper = Scraper()
scraper.run()