from src.shared.logger import load_logger
from src.simpcity import SimpCity

if __name__ == "__main__":
    load_logger()

    simpcity = SimpCity()
    simpcity.scrape()