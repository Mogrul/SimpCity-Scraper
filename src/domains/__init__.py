from .domain import Domain
from .gofile import GoFile
from .goonbox import GoonBox
from .turbo import Turbo
from .cyberdrop import CyberDrop


DOMAINS: dict[str, type[Domain]] = {
    "goonbox.cr": GoonBox,
    "turbo.cr": Turbo,
    "cyberdrop.cr": CyberDrop,
    "gofile.io": GoFile
}