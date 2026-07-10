import logging

from src.core.util import find_subclasses, get_domain_name
from src.core.site.site import Site
from src.core.session import Session

class Core:
    def __init__(self):
        self.logger = logging.getLogger("core")
        self.session = Session()
        self.sites: dict[str, type[Site]] = find_subclasses("src.core.site", Site)
    
    def scrape(self, url: str):
        domain_name = get_domain_name(url)
        
        if domain_name not in self.sites:
            self.logger.warning(f"Site not supported ({domain_name}): {url}")
            return
        
        site = self.sites.get(domain_name)
        if not site:
            self.logger.error(f"Failed to get site: {site}")
            return
        
        site = site(
            url = url,
            sites = self.sites,
            session = self.session
        )
        site.scrape()
        