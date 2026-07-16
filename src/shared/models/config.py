from dataclasses import dataclass

from .duplication import Duplication
from .network import Network
from .scraper import Scraper

@dataclass
class Config:
    duplication: Duplication
    network: Network
    scraper: Scraper