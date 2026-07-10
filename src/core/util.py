import importlib
import inspect
import pkgutil
from pathlib import Path

import tldextract

def find_subclasses(package_name: str, base_class: type) -> dict[str, type]:
    package = importlib.import_module(package_name)

    classes = {}

    for _, module_name, _ in pkgutil.walk_packages(
        package.__path__,
        package.__name__ + ".",
    ):
        module = importlib.import_module(module_name)

        for _, cls in inspect.getmembers(module, inspect.isclass):
            if (
                cls.__module__ == module.__name__
                and issubclass(cls, base_class)
                and cls is not base_class
            ):
                key = module.__name__.rsplit(".", 1)[-1]
                classes[key] = cls

    return classes

def get_domain_name(url: str) -> str:
    extracted = tldextract.extract(url)
    
    return extracted.domain

def is_image(path: Path) -> bool:
    if not path.is_file():
        return False
    
    img_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    
    if path.suffix.lower() in img_extensions:
        return True
    
    return False