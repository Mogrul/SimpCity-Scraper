from .website import WebSite

from .goonbox import GoonBox
from .turbo import Turbo
from .bunkr import Bunkr

WEBSITES: dict[str, type[WebSite]] = {
    "goonbox": GoonBox,
    "turbo": Turbo,
    "bunkr": Bunkr,
    "simpcity": WebSite
}