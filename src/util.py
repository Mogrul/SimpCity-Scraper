from pathlib import Path


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.3f}s"
    elif seconds < 3600:
        minutes, seconds = divmod(seconds, 60)
        return f"{int(minutes)}m {seconds:.1f}s"
    elif seconds < 86400:
        hours, remainder = divmod(seconds, 3600)
        minutes = remainder // 60
        return f"{int(hours)}h {int(minutes)}m"
    else:
        days, remainder = divmod(seconds, 86400)
        hours = remainder // 3600
        return f"{int(days)}d {int(hours)}h"

def format_bytes(amount: int) -> str:
    value = float(amount)

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

def is_video(path: Path):
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