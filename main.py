from src.shared import load_logger, Config
from src.simpcity.simpcity import SimpCity
from src.database.database import Database
from src.http.client import HTTPClient

if __name__ == "__main__":
    logger = load_logger()
    
    c = Config()
    c.load_config()
    
    db = Database()
    db.load_duplicates()
    db.load_extracted()
    
    client = HTTPClient()
    
    ss = SimpCity()
    ss.run()
