from .domain import Domain
from .goonbox import GoonBox
from .turbo import Turbo

DOMAINS: dict[str, type[Domain]] = {
    "goonbox.cr": GoonBox,
    "turbo.cr": Turbo
}