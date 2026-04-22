"""SQLite storage module for DevPulse.

This module provides persistent storage for articles using SQLite with:
- Full-text search (FTS5) for efficient content search
- Automatic triggers for search index synchronization
- Saved articles bookmarking functionality

The database schema includes:
- articles: Main article storage with metadata
- saved: Bookmark tracking for saved articles
- articles_fts: FTS5 virtual table for full-text search

Example:
    storage = SQLiteStorage()
    storage.add_article('Title', 'http://example.com', 'source', 75.0, 'Content')
    articles = storage.list_articles(limit=10)
    results = storage.search_articles('kubernetes')
"""

import sqlite3
from datetime import datetime
from typing import Optional
from devpulse.config import config
from devpulse.core.logging_config import get_logger

logger = get_logger(__name__)


class SQLiteStorage:
    """SQLite storage implementation with FTS5 full-text search.
    
    This class handles all database operations for DevPulse including:
    - Article storage and retrieval
    - Full-text search using FTS5
    - Saved article bookmarking
    - Database initialization and schema management
    
    Attributes:
        db_path: Path to the SQLite database file
    
    Example:
        >>> storage = SQLiteStorage()
        >>> storage.add_article('Kubernetes Guide', 'http://example.com', 'Blog', 85.0, 'Content...')
        >>> articles = storage.list_articles(limit=5)
    """
    
    def __init__(self) -> None:
        """Initialize SQLite storage and create database schema if needed."""
        self.db_path = config.db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection.
        
        Returns:
            SQLite connection object.
        """
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        """Initialize database schema.
        
        Creates the following tables and triggers:
        - articles: Main article storage
        - saved: Saved article bookmarks
        - articles_fts: FTS5 virtual table for full-text search
        - articles_ai: Trigger to sync INSERT to FTS
        - articles_au: Trigger to sync UPDATE to FTS
        
        Raises:
            sqlite3.Error: If database initialization fails.
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        url TEXT UNIQUE,
                        source TEXT,
                        score REAL,
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
                conn.execute("DROP TRIGGER IF EXISTS articles_au")
                conn.execute("""
                    CREATE TRIGGER articles_au AFTER UPDATE ON articles BEGIN
                        INSERT INTO articles_fts(articles_fts, rowid, title, content, source)
                        VALUES('delete', old.id, old.title, old.content, old.source);
                        INSERT INTO articles_fts(rowid, title, content, source)
                        VALUES(new.id, new.title, new.content, new.source);
                    END
                """)
            logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}", exc_info=True)
            raise

    def clear_articles(self) -> None:
        """Wipe all articles and reset the search index.
        
        This removes all articles from the database and clears the FTS index.
        Saved article bookmarks are preserved.
        
        Raises:
            sqlite3.Error: If the operation fails.
        """
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM articles")
                conn.execute("DELETE FROM articles_fts")
            logger.info("Cleared all articles")
        except sqlite3.Error as e:
            logger.error(f"Error clearing articles: {e}", exc_info=True)
            raise

    def add_article(self, title: str, url: str, source: str, score: float, content: str) -> Optional[int]:
        """Add an article to storage.
        
        Args:
            title: Article title
            url: Article URL (must be unique)
            source: Source name (e.g., 'Kubernetes Blog')
            score: Relevance score
            content: Article content/body
        
        Returns:
            Article ID if successfully added, None if duplicate or error.
        
        Example:
            >>> storage.add_article('K8s Guide', 'http://example.com', 'Blog', 85.0, 'Content...')
            123
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO articles (title, url, source, score, content) 
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (title, url, source, score, content)
                )
                if cursor.lastrowid:
                    logger.debug(f"Added article: {title[:50]}...")
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error adding article {url}: {e}", exc_info=True)
            return None

    def list_articles(self, limit: int = 20, offset: int = 0) -> list:
        """List articles ordered by score and freshness.
        
        Args:
            limit: Maximum number of articles to return
            offset: Number of articles to skip (for pagination)
        
        Returns:
            List of article dictionaries ordered by fetched_at DESC, score DESC.
        
        Example:
            >>> storage.list_articles(limit=5)
            [{'id': 1, 'title': '...', ...}, ...]
        """
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                return conn.execute(
                    "SELECT * FROM articles ORDER BY fetched_at DESC, score DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                ).fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error listing articles: {e}", exc_info=True)
            return []

    def get_article(self, article_id: int) -> Optional[dict]:
        """Get a single article by ID.
        
        Args:
            article_id: The article ID to retrieve
        
        Returns:
            Article dictionary if found, None otherwise.
        
        Example:
            >>> storage.get_article(123)
            {'id': 123, 'title': 'Kubernetes Guide', ...}
        """
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting article {article_id}: {e}", exc_info=True)
            return None

    def save_article(self, article_id: int) -> None:
        """Mark an article as saved (bookmark).
        
        Args:
            article_id: The article ID to save
        
        Raises:
            sqlite3.Error: If the operation fails.
        """
        try:
            with self._get_connection() as conn:
                conn.execute("INSERT OR IGNORE INTO saved (id) VALUES (?)", (article_id,))
            logger.debug(f"Saved article {article_id}")
        except sqlite3.Error as e:
            logger.error(f"Error saving article {article_id}: {e}", exc_info=True)
            raise

    def get_saved_articles(self) -> list:
        """Get all saved articles.
        
        Returns:
            List of saved article dictionaries ordered by save time DESC.
        
        Example:
            >>> storage.get_saved_articles()
            [{'id': 1, 'title': '...', ...}, ...]
        """
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                return conn.execute(
                    "SELECT a.* FROM articles a JOIN saved s ON a.id = s.id ORDER BY s.saved_at DESC"
                ).fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting saved articles: {e}", exc_info=True)
            return []

    def search_articles(self, query: str) -> list:
        """Search articles using FTS5 full-text search.
        
        Uses SQLite FTS5 BM25 ranking algorithm combined with article scores.
        
        Args:
            query: FTS5 search query (supports boolean operators, phrases, etc.)
        
        Returns:
            List of matching article dictionaries with rank and score.
        
        Example:
            >>> storage.search_articles('kubernetes deployment')
            [{'id': 1, 'title': '...', 'rank': 0.5, ...}, ...]
        """
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
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
            logger.error(f"Search error for query '{query}': {e}", exc_info=True)
            return []
