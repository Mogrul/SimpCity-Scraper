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

    return parser.parse_args()