from .external import External

from .goonbox import GoonBox

EXTERNALS: dict[str, type[External]] = {
    "goonbox.cr": GoonBox
}