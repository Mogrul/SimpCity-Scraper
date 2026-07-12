from .website import WebSite

from .goonbox import GoonBox
from .turbo import Turbo

WEBSITES: dict[str, type[WebSite]] = {
    "goonbox": GoonBox,
    #"turbo": Turbo,
    "simpcity": WebSite
}