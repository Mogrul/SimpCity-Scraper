from .models import *

from .domain import Domain
from .bunkr import Bunkr
from .gofile import GoFile
from .goonbox import GoonBox
from .pixeldrain import PixelDrain
from .turbo import Turbo
from .cyberdrop import CyberDrop


DOMAINS: dict[str, type[Domain]] = {
    "goonbox.cr": GoonBox,
    "turbo.cr": Turbo,
    "cyberdrop.cr": CyberDrop,
    "gofile.io": GoFile,
    "bunkr.cr": Bunkr,
    "pixeldrain.com": PixelDrain,
}