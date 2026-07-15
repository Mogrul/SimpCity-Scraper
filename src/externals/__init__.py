from .external import External

from .goonbox import GoonBox
from .bunkr import Bunkr

EXTERNALS: dict[str, type[External]] = {
    "goonbox.cr": GoonBox,
    "bunkr.cr": Bunkr
}