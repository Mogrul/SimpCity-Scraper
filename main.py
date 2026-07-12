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
    os._exit(0)
    url = "https://cyberdrop.cr/e/H7iuJcmRs2oNx"
    id = url.split("/")[-1]
    
    from src.web import Web
    
    w = Web()
    print(w.get(
        url = f"https://api.cyberdrop.cr/api/file/auth/{id}",
        return_dict = True
    ))