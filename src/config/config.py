import argparse
import logging
import tomllib
import os
from pathlib import Path

from .models import *

def load_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = "Scrape SimpCity Links"
    )

    parser.add_argument(
        "links",
        nargs = "*",
        metavar = "link",
        help = "SimpCity Links"
    )

    parser.add_argument(
        "-pc", "--print-config",
        action = "store_true",
        help = "Prints the current configuration"
    )

    parser.add_argument(
        "-cd", "--check-duplicates",
        metavar = "PATH",
        type = Path,
        help = "Check for duplicate files in PATH"
    )

    parser.add_argument(
        "-i", "--images",
        action = "store_true",
        help = "Check duplicate images"
    )

    parser.add_argument(
        "-v", "--videos",
        action = "store_true",
        help = "Check duplicate videos"
    )

    return parser.parse_args()


class Config:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):
        if getattr(self, "thread_count", False):
            return

        self.logger = logging.getLogger("Config")

        thread_count = os.process_cpu_count()
        self.thread_count = (
            4 if not thread_count
            else int(thread_count / 2)
        )
        self.links: list[str] = []

        self.network = NetworkConfig(
            timeout = 10,
            chunk_size = 1048576,
            cookies = Path(".cookies"),
            headers = {}
        )

        self.downloads = DownloadConfig(
            location = Path("Downloads"),
            skip_domains = [],
            watched_threads = True
        )

        self.database = DatabaseConfig(
            enabled = True,
            location = Path("data/data.db"),
        )

        self.duplication = DuplicationConfig(
            images = True,
            videos = True,
            ffmpeg_path = Path("C:\\ffmpeg\\bin\\ffmpeg.exe"),
            ffprobe_path = Path("C:\\ffmpeg\\bin\\ffprobe.exe"),
            threshold = 0.9,
            samples = 3
        )

    def load_config(self, config_path = Path('config.toml')):
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        self.links.extend(data.get("links", []))

        # Download configs
        downloads = data.get("downloads", {})
        download_location = downloads.get("location", "Downloads")
        skip_domains = downloads.get("skip_domains", [])
        watched_thread = downloads.get("watched_threads", False)

        # Network configs
        network = data.get("network", {})
        network_timeout = network.get("timeout", 10)
        network_chunk_size = network.get("chunk_size", 1048576)
        network_cookies = network.get("cookies", ".cookies")
        network_headers = network.get("headers", {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive"
        })

        # Database configs
        database = data.get("database", {})
        enabled = database.get("enabled", True)
        location = database.get("location", "data/data.db")

        # Duplication configs
        duplication = data.get("duplication", {})
        images = duplication.get("images", True)
        videos = duplication.get("videos", True)
        ffmpeg_path = duplication.get("ffmpeg_path", "C:\\ffmpeg\\bin\\ffmpeg.exe")
        ffprobe_path = duplication.get("ffprobe_path", "C:\\ffmpeg\\bin\\ffprobe.exe")
        threshold = duplication.get("threshold", 0.9)
        samples = duplication.get("samples", 3)

        # Arg configs
        args = load_args()
        self.links.extend(args.links)

        self.network = NetworkConfig(
            timeout = network_timeout,
            chunk_size = network_chunk_size,
            cookies = Path(network_cookies),
            headers = network_headers
        )

        self.downloads = DownloadConfig(
            location = Path(download_location),
            skip_domains = skip_domains,
            watched_threads = watched_thread
        )

        self.database = DatabaseConfig(
            enabled = enabled,
            location = Path(location)
        )

        self.duplication = DuplicationConfig(
            images = images,
            videos = videos,
            ffmpeg_path = Path(ffmpeg_path),
            ffprobe_path = Path(ffprobe_path),
            threshold = threshold,
            samples = samples
        )

        # Finally handle args
        self.handle_args(args)

    def handle_args(self, args: argparse.Namespace):
        if (
            not self.links
            and not self.downloads.watched_threads
            and not args.print_config
            and not args.check_duplicates
        ):
            self.logger.critical(f"URL arguments or watched_thread in config required, do --help for more information.")
            os.abort()

        if args.print_config:
            # Print config
            self.logger.info(
                "Program Configuration:\n"
                f"          {f'Thread Limit:':<26} {self.thread_count:<20}\n\n"
                "          Downloads:\n"
                f"                {f'Download Location:':<20} {str(self.downloads.location):<20}\n"
                f"                {f'Skip Domains:':<20} {str(self.downloads.skip_domains):<20}\n"
                f"                {f'Watched Threads:':<20} {str(self.downloads.watched_threads):<20}\n\n"
                f"          Database:\n"
                f"                {f'Enabled:':<20} {str(self.database.enabled):<20}\n"
                f"                {f'Location:':<20} {str(self.database.location):<20}\n\n"
                "          Duplication:\n"
                f"                {f'Images':<20} {str(self.duplication.images):<20}\n"
                f"                {f'Videos':<20} {str(self.duplication.videos):<20}\n"
                f"                {f'Threshold:':<20} {str(self.duplication.threshold):<20}\n"
                f"                {f'Samples:':<20} {str(self.duplication.samples):<20}\n"
                f"                {f'FFMPEG Path:':<20} {str(self.duplication.ffmpeg_path):<20}\n"
                f"                {f'FFProbe Path:':<20} {str(self.duplication.ffprobe_path):<20}\n\n"
                "          Network:\n"
                f"                {f'Timeout:':<20} {str(self.network.timeout):<20}\n"
                f"                {f'Chunk Size:':<20} {str(self.network.chunk_size):<20}\n"
                f"                {f'Cookies:':<20} {str(self.network.cookies):<20}\n"
            )
            os.abort()

        if args.check_duplicates:
            if not args.images and not args.videos:
                self.logger.error(f"When using --check_duplicates, you must select and or -i for images, -v for videos")
                os.abort()

            path = args.check_duplicates

            from duplication import Duplication
            duplication = Duplication(path, {})

            if args.images:
                duplication.check_images()

            if args.videos:
                duplication.check_videos()