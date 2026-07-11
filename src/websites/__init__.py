from .website import WebSite

from .goonbox import GoonBox

WEBSITES: dict[str, type[WebSite]] = {
    "goonbox.cr": GoonBox
}