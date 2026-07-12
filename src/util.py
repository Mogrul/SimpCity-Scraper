from urllib.parse import urlparse
from pathlib import Path

import tldextract

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )

    except Exception:
        return False

def format_bytes(size: int) -> str:
    value = float(size)
    
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.2f} {unit}"
                
        value /= 1024

    return f"{value:.2f} PB"

def is_image(path: Path) -> bool:
    if not path.is_file():
        return False
    
    img_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    
    if path.suffix.lower() in img_extensions:
        return True
    
    return False

def is_video(path: Path) -> bool:
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
    return tldextract.extract(url).domain