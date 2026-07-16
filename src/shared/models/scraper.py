from dataclasses import dataclass, field

from pathlib import Path

@dataclass
class Scraper:
    download_location: Path
    extractor_location: Path
    extract_files: bool
    skip_scrapers: list[str] = field(default_factory = list)