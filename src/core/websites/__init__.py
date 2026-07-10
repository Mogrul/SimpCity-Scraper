from .website import Website

from .goonbox import GoonBox
from .bunkr import Bunkr

WEBSITES: dict[str, type[Website]] = {
    "goonbox": GoonBox,
    "bunkr": Bunkr
}