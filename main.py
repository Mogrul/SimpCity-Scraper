from src.core import Core
from src.logger import load_logger

if __name__ == "__main__":
    load_logger()
    
    core = Core()
    core.scrape("https://simpcity.cr/threads/aiwa-aiwa_only-truegspot-yoursexylady18-aiwaonly.15084/")