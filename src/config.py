from argparse import Namespace
from pathlib import Path

URLS: list[str] = []
OUTPUT: Path = Path()
WORKERS: int = 0
TIMEOUT: int = 30
REMOVE_DUPLICATES: bool = True
CHUNK_SIZE: int = 1_048_576
EXCLUDE_DOMAINS: list[str] = []

def set_args(args: Namespace):
    global URLS, OUTPUT, TIMEOUT, REMOVE_DUPLICATES, CHUNK_SIZE, EXCLUDE_DOMAINS, WORKERS
    
    URLS = args.urls
    OUTPUT = args.output
    TIMEOUT = args.timeout
    REMOVE_DUPLICATES = bool(args.remove_duplicates)
    CHUNK_SIZE = args.chunk_size
    EXCLUDE_DOMAINS = args.exclude
    WORKERS = args.workers