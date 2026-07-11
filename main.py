from src.shared.logger import load_logger
from src.simpcity import SimpCity

if __name__ == "__main__":
    load_logger()

    simpcity = SimpCity([
        "https://simpcity.cr/threads/aiwa-aiwa_only-truegspot-yoursexylady18-aiwaonly.15084",
        "https://pypi.org/project/ImageHash/"
    ])
    simpcity.scrape()