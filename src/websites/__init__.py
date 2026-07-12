from .website import WebSite

from .goonbox import GoonBox
from .turbo import Turbo
from .bunkr import Bunkr
from .cyberdrop import CyberDrop
from .pixeldrain import PixelDrain

WEBSITES: dict[str, type[WebSite]] = {
    "goonbox": GoonBox,
    "turbo": Turbo,
    "cyberdrop": CyberDrop,
    "bunkr": Bunkr,
    "pixeldrain": PixelDrain,
    "simpcity": WebSite
}