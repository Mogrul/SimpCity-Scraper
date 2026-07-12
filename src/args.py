import argparse
from argparse import Namespace
from pathlib import Path

def parse_args() -> Namespace:
        parser = argparse.ArgumentParser(
            description = "Download files from simpcity."
        )
        
        # Multi-arguments
        parser.add_argument(
            "urls",
            nargs = "+",
            metavar = "URL",
            help = "One or more URLs to scrape."
        )
        
        parser.add_argument(
            "-e", "--exclude",
            nargs = "+",
            metavar = "DOMAIN",
            help = "A list of domains to exclude when scraping."
        )
        
        # Str arguments
        parser.add_argument(
            "-rd", "--remove-duplicates",
            type = str,
            default = True,
            help = "To check for duplicates after scraping a URL (default: True)."
        )
        
        # Path arguments
        parser.add_argument(
            "-o", "--output",
            type = Path,
            default = Path("Downloads"),
            help = "Output directory where files are downloaded (default: Downloads)"
        )
        
        # Int arguments
        parser.add_argument(
            "-w", "--workers",
            type = int,
            default = 10,
            help = "Maximum concurrent workers (default: 10)."
        )

        parser.add_argument(
            "--timeout",
            type = int,
            default = 30,
            help = "HTTP timeout in seconds (default: 30)."
        )
        
        parser.add_argument(
            "-cs", "--chunk-size",
            type = int,
            default = 1_048_576,
            help = "Chunk size to download files in (default: 1_048_576)."
        )
        
        return parser.parse_args()