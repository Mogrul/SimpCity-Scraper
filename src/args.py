import argparse
from argparse import Namespace

def parse_args() -> Namespace:
    """Passes the arguments sent to the executable to use in-code.

    Returns:
        Namespace: The namespace of the arguments to retrieve data.
    """
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