import logging
import sqlite3

from config import Config


class Database:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):
        if getattr(self, "_initialised", False):
            return
        self._initialised = True

        self.logger = logging.getLogger("database")
        self.config = Config().database

        if not self.config.location.exists():
            self.config.location.parent.mkdir(parents = True, exist_ok = True)

        self.completed: set[str] = set()
        self.connection = sqlite3.connect(self.config.location)
        self.connection.row_factory = sqlite3.Row

        self.generate_tables()
        self.load_completed()

    def generate_tables(self):
        q = """
            CREATE TABLE IF NOT EXISTS `completed` (
                link TEXT PRIMARY KEY
            );
        """

        self.connection.execute(q)
        self.connection.commit()

    def load_completed(self):
        q = """
            SELECT * FROM completed
        """

        rows = self.connection.execute(q).fetchall()
        for row in rows:
            self.completed.add(row["link"])

        self.logger.info(f"Added {len(self.completed)} completed links to cache")

    def add_completed(self, link: str):
        q = """
            INSERT OR IGNORE INTO completed (link) VALUES (?)
        """

        self.connection.execute(q, (link,))
        self.connection.commit()