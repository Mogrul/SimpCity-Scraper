import argparse
import tomllib
import os
from pathlib import Path

from models import Network, Downloads


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

        thread_count = os.process_cpu_count()
        self.thread_count = (
            4 if not thread_count
            else int(thread_count / 2)
        )
        self.links: list[str] = []

        self.network = Network(
            timeout = 10,
            chunk_size = 1048576,
            cookies = Path(".cookies"),
            headers = {}
        )

        self.downloads = Downloads(
            location = Path("Downloads"),
        )

    def load_config(self, config_path = Path('config.toml')):
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        # Download configs
        downloads = data.get("downloads", {})
        download_location = downloads.get("location", "Downloads")

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

        # Arg configs
        args = load_args()
        self.links = args.links

        self.network = Network(
            timeout = network_timeout,
            chunk_size = network_chunk_size,
            cookies = Path(network_cookies),
            headers = network_headers
        )

        self.downloads = Downloads(
            location = Path(download_location),
        )
