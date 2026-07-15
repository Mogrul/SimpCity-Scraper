from .external import External

from .goonbox import GoonBox
from .bunkr import Bunkr
from .turbo import Turbo

EXTERNALS: dict[str, type[External]] = {
    "goonbox.cr": GoonBox,
    "bunkr.cr": Bunkr,
    "turbo.cr": Turbo
}