from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid3, NAMESPACE_DNS

from .models import Post

ROOT_PATH = Path("Downloads")
    

def get_post_path(post: Post, username: str) -> Path:
    return Path(
        ROOT_PATH,
        username,
        str(post.posted_at.year)
    )

def get_path_of_file(post: Post, file_name: str, username: str) -> Path:
    post_path = get_post_path(post, username)
    file = Path(file_name)
    file_id = str(uuid3(NAMESPACE_DNS, file_name))[:8]
    posted_at = post.posted_at
    
    return Path(
        post_path,
        f"[{posted_at.year}-{posted_at.month:02d}-{posted_at.day:02d}] {file_id}{file.suffix}"
    )

def get_username_from_url(url: str):
    path = urlparse(url).path
    
    thread = path.split("/")[-2]
    
    if "-" in thread:
        return thread.split("-")[0]

    else:
        return thread

def is_image(path: Path) -> bool:
    if not path.is_file():
        return False
    
    img_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    
    if path.suffix.lower() in img_extensions:
        return True
    
    return False

def split_into_groups(items: list, size = 5):
    return [
        items[i:i + size]
        for i in range(0, len(items), size)
    ]