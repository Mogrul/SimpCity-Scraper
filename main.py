from src.shared.logger import load_logger
from src.simpcity import SimpCity
from src.args import parse_args

from src.shared.config import Config

import os

if __name__ == "__main__":
    load_logger()
    
    args = parse_args()
    
    config = Config()
    success = config.load_config(args)
    
    if not success:
        os._exit(0)
    
    success = config.verify_config()
    
    if not success:
        os._exit(0)

    simpcity = SimpCity()
    simpcity.scrape()