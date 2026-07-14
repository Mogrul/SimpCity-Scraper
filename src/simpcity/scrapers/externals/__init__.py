from .external_scraper import ExternalScraper

from .goonbox import GoonBox
from .turbo import Turbo

EXTERNAL_SCRAPERS: dict[str, type[ExternalScraper]] = {
    "goonbox.cr": GoonBox,
    "turbo.cr": Turbo
}