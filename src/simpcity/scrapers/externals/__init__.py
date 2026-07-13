from .external_scraper import ExternalScraper

from .goonbox import GoonBox

EXTERNAL_SCRAPERS: dict[str, type[ExternalScraper]] = {
    "goonbox.cr": GoonBox
}