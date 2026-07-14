import argparse

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = "Scraped SimpCity URLS"
    )
    
    parser.add_argument(
        "urls",
        nargs = "+",
        metavar = "URLs",
        help = "SimpCity URLs"
    )
    
    return parser.parse_args()