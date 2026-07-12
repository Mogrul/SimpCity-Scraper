from src.shared.logger import load_logger
from src.simpcity import SimpCity
from src.args import parse_args

from src import config

if __name__ == "__main__":
    args = parse_args()
    config.set_args(args)
    load_logger()

    simpcity = SimpCity()
    simpcity.scrape()