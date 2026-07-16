from .domain import Domain
from .goonbox import GoonBox

DOMAINS: dict[str, type[Domain]] = {
    "goonbox.cr": GoonBox
}