import argparse
import os

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = "Scraped SimpCity URLS"
    )
    
    parser.add_argument(
        "urls",
        nargs = "*",
        metavar = "URLs",
        help = "SimpCity URLs"
    )
    
    parser.add_argument(
        "-c", "--config",
        action = "store_true",
        help = "Retrieves config values"
    )
    
    args = parser.parse_args()
    
    if not args.config and not args.urls:
        parser.error("Invalid arguments, do --help")
        os.abort()
    
    return args
    