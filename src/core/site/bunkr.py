import logging

from .site import Site

class Bunkr(Site):
    def __init__(self, *args, **kwargs):
        super().__init__(logger = logging.getLogger("site.bunkr"), *args, **kwargs)