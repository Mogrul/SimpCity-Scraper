from dataclasses import dataclass

@dataclass
class DomainStats:
    marked_extracted: int
    marked_duplicate: int
    extracted: int
    downloaded: int
    failed: int
    existing: int
    total: int
    
    def __iadd__(self, other: "DomainStats"):
        self.marked_extracted += other.marked_extracted
        self.marked_duplicate += other.marked_duplicate
        self.extracted += other.extracted
        self.downloaded += other.downloaded
        self.existing += other.existing
        self.failed += other.failed
        return self