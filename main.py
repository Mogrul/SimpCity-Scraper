from src.shared.logger import load_logger
from src.simpcity import SimpCity
from src.args import parse_args

if __name__ == "__main__":
    args = parse_args()
    load_logger()

    simpcity = SimpCity(args)
    simpcity.scrape()