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
        try:
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
                # Add update trigger for FTS
                conn.execute("DROP TRIGGER IF EXISTS articles_au")
                conn.execute("""
                    CREATE TRIGGER articles_au AFTER UPDATE ON articles BEGIN
                        INSERT INTO articles_fts(articles_fts, rowid, title, content, source)
                        VALUES('delete', old.id, old.title, old.content, old.source);
                        INSERT INTO articles_fts(rowid, title, content, source)
                        VALUES(new.id, new.title, new.content, new.source);
                    END
                """)
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
            raise

    def clear_articles(self):
        """Wipe all articles and reset the search index."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM articles")
                conn.execute("DELETE FROM articles_fts")
                # We keep the 'saved' table to preserve user bookmarks
        except sqlite3.Error as e:
            print(f"Error clearing articles: {e}")

    def add_article(self, title, url, source, score, content):
        try:
            with self._get_connection() as conn:
                # Basic INSERT because we clear before fetching now
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO articles (title, url, source, score, content) 
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (title, url, source, score, content)
                )
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding article: {e}")
            return None

    def list_articles(self, limit=20, offset=0):
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                return conn.execute(
                    "SELECT * FROM articles ORDER BY fetched_at DESC, score DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                ).fetchall()
        except sqlite3.Error as e:
            print(f"Error listing articles: {e}")
            return []

    def get_article(self, article_id):
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                return conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        except sqlite3.Error as e:
            print(f"Error getting article {article_id}: {e}")
            return None

    def save_article(self, article_id):
        try:
            with self._get_connection() as conn:
                conn.execute("INSERT OR IGNORE INTO saved (id) VALUES (?)", (article_id,))
        except sqlite3.Error as e:
            print(f"Error saving article {article_id}: {e}")

    def get_saved_articles(self):
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                return conn.execute(
                    "SELECT a.* FROM articles a JOIN saved s ON a.id = s.id ORDER BY s.saved_at DESC"
                ).fetchall()
        except sqlite3.Error as e:
            print(f"Error getting saved articles: {e}")
            return []

    def search_articles(self, query):
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                # Optimized search: Rank by BM25 (built-in FTS5) combined with our custom score
                return conn.execute(
                    """
                    SELECT a.*, rank 
                    FROM articles a 
                    JOIN articles_fts f ON a.id = f.rowid 
                    WHERE articles_fts MATCH ? 
                    ORDER BY rank, a.score DESC
                    """,
                    (query,)
                ).fetchall()
        except sqlite3.Error as e:
            print(f"Search error for query '{query}': {e}")
            return []

storage = Storage()
