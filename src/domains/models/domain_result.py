from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class DomainResult:
    downloaded: int
    duplicate: int
    failed: int
    completed_links: dict[Path, str] = field(default_factory = dict)

    def __iadd__(self, other: "DomainResult") -> DomainResult:
        self.downloaded += other.downloaded
        self.duplicate += other.duplicate
        self.failed += other.failed

        return self