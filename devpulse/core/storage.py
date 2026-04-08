import sqlite3
from datetime import datetime
from devpulse.config import config

class Storage:
    def __init__(self):
        self.db_path = config.db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    url TEXT UNIQUE,
                    source TEXT,
                    score INTEGER,
                    content TEXT,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saved (
                    id INTEGER PRIMARY KEY,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(id) REFERENCES articles(id)
                )
            """)
            # FTS5 for search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                    title, content, source, content='articles', content_rowid='id'
                )
            """)
            # Triggers for FTS
            conn.execute("DROP TRIGGER IF EXISTS articles_ai")
            conn.execute("""
                CREATE TRIGGER articles_ai AFTER INSERT ON articles BEGIN
                    INSERT INTO articles_fts(rowid, title, content, source) 
                    VALUES (new.id, new.title, new.content, new.source);
                END
            """)

    def add_article(self, title, url, source, score, content):
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO articles (title, url, source, score, content) VALUES (?, ?, ?, ?, ?)",
                    (title, url, source, score, content)
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def list_articles(self, limit=20, offset=0):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM articles ORDER BY score DESC, fetched_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()

    def get_article(self, article_id):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()

    def save_article(self, article_id):
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO saved (id) VALUES (?)", (article_id,))

    def get_saved_articles(self):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT a.* FROM articles a JOIN saved s ON a.id = s.id ORDER BY s.saved_at DESC"
            ).fetchall()

    def search_articles(self, query):
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM articles WHERE id IN (SELECT rowid FROM articles_fts WHERE articles_fts MATCH ?) ORDER BY score DESC",
                (query,)
            ).fetchall()

storage = Storage()
