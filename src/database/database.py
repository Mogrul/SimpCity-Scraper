from pathlib import Path
import sqlite3
import logging

from src.shared import SingletonMeta
from .models import DuplicateItem

class Database(metaclass = SingletonMeta):
    def __init__(self, database_path = Path("data/data.db")):
        self._logger = logging.getLogger("database")
        
        if not database_path.exists():
            database_path.parent.mkdir(parents = True, exist_ok = True)
            self._logger.info(f"Created root path for {database_path}")
        
        self._connection = sqlite3.connect(
            database_path,
            check_same_thread = False
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        
        # Create default table if not exist
        self.create_default_table()
        
        # deleted path -> DuplicateItem
        self.duplicate_items: dict[Path, DuplicateItem] = {}
        
        self._logger.info(f"Connected to {database_path}")
    
    def create_default_table(self):
        q = """
            CREATE TABLE IF NOT EXISTS duplicates (
                kept_path TEXT,
                deleted_path TEXT,
                kept_size INT,
                deleted_size INT,
                similarity INT
            )
        """
        
        self._connection.execute(q)
        self._connection.commit()
    
    def add_duplicate(self, item: DuplicateItem):
        q = """
            INSERT INTO duplicates
            VALUES (?, ?, ?, ?, ?)
        """
        
        self._connection.execute(
            q,
            (
                str(item.kept_path),
                str(item.deleted_path),
                item.kept_size,
                item.deleted_size,
                int(item.similarity * 100)
            )
        )
        
        self._connection.commit()
    
    def load_duplicates(self):
        q = """
            SELECT * FROM duplicates
        """
        
        rows = self._connection.execute(q).fetchall()
        
        for row in rows:
            kept_path = Path(row["kept_path"])
            deleted_path = Path(row["deleted_path"])
            kept_size = row["kept_size"]
            deleted_size = row["deleted_size"]
            similarity = row["similarity"]
            
            self.duplicate_items[deleted_path] = DuplicateItem(
                kept_path = kept_path,
                deleted_path = deleted_path,
                kept_size = kept_size,
                deleted_size = deleted_size,
                similarity = similarity / 100
            )
        
        self._logger.info(f"Added {len(self.duplicate_items)} duplicate items to cache")
        
        
        