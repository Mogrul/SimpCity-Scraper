from urllib.parse import urlparse
from pathlib import Path
import sys
import os

import tldextract

def is_valid_url(url: str) -> bool:
    """Validates a URL string by checking for http/https and network location.

    Args:
        url (str): URL to check

    Returns:
        bool: True if pass, False if not.
    """
    try:
        parsed = urlparse(url)

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )

    except Exception:
        return False

def format_bytes(size: int) -> str:
    """Formats a bytes integer into a clean str

    Args:
        size (int): Bytes in int to format.

    Returns:
        str: Formatted size string (10B/10KB/10MB)
    """
    value = float(size)
    
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.2f} {unit}"
                
        value /= 1024

    return f"{value:.2f} PB"

def is_image(path: Path) -> bool:
    """Checks a path object to verify if it's an image.

    Args:
        path (Path): Path to check if it's an image.

    Returns:
        bool: True if it is, False if it's not.
    """
    if not path.is_file():
        return False
    
    img_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    
    if path.suffix.lower() in img_extensions:
        return True
    
    return False

def is_video(path: Path) -> bool:
    """Checks if a path is a video or not.

    Args:
        path (Path): Path to check if it's a video.

    Returns:
        bool: True if it is, False if it's not.
    """
    if not path.is_file():
        return False
    
    video_extensions = {
        ".mp4", ".mkv", ".avi", ".mov",
        ".webm", ".wmv", ".flv",
        ".m4v", ".mpeg", ".mpg"
    }
    
    if path.suffix.lower() in video_extensions:
        return True
    
    return False

def get_domain_name(url: str) -> str:
    """Extracts a readable domain string from a URL string.

    Args:
        url (str): Full URL string to obtain domain name from.

    Returns:
        str: Readable domain name (simpcity)
    """
    return tldextract.extract(url).domain

def resource_path(relative_path: str) -> Path:
    """Converts a relative path string to a usable Path object for pyinstaller.

    Args:
        relative_path (str): Relative path of a resource (logs/latest.log)

    Returns:
        Path: Path object of the relative path.
    """
    if getattr(sys, "frozen", False):
        # Running as bundled executable
        base_path = Path(sys.executable).parent
    
    else:
        # Running from source
        base_path = Path(os.getcwd())
    
    return base_path / relative_path