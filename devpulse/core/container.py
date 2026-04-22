"""Dependency injection container for DevPulse components."""
import logging
from typing import Protocol
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class StorageProtocol(Protocol):
    """Protocol for storage implementations."""
    def add_article(self, title: str, url: str, source: str, score: float, content: str) -> int | None: ...
    def list_articles(self, limit: int = 20, offset: int = 0) -> list: ...
    def get_article(self, article_id: int) -> dict | None: ...
    def save_article(self, article_id: int) -> None: ...
    def get_saved_articles(self) -> list: ...
    def search_articles(self, query: str) -> list: ...
    def clear_articles(self) -> None: ...


class ScorerProtocol(Protocol):
    """Protocol for scorer implementations."""
    def calculate_score(self, article: dict, topic: str | None = None) -> float: ...
    def is_relevant(self, score: float) -> bool: ...


class FetcherProtocol(Protocol):
    """Protocol for fetcher implementations."""
    def fetch_all(self, topic: str | None = None) -> int: ...


@dataclass
class Container:
    """Dependency injection container for DevPulse components."""
    storage: StorageProtocol
    scorer: ScorerProtocol
    fetcher: FetcherProtocol


def create_container() -> Container:
    """Create and initialize the DI container with all components."""
    from devpulse.core.storage import SQLiteStorage
    from devpulse.core.scorer import ArticleScorer
    from devpulse.core.fetcher import ArticleFetcher
    
    logger.info("Initializing dependency injection container")
    
    # Initialize components in dependency order
    storage = SQLiteStorage()
    scorer = ArticleScorer()
    fetcher = ArticleFetcher(storage=storage, scorer=scorer)
    
    logger.info("Container initialized successfully")
    return Container(storage=storage, scorer=scorer, fetcher=fetcher)


# Global container instance (initialized on first use)
_container: Container | None = None


def get_container() -> Container:
    """Get or create the global container instance."""
    global _container
    if _container is None:
        _container = create_container()
    return _container


def reset_container() -> None:
    """Reset the global container (useful for testing)."""
    global _container
    _container = None
    logger.debug("Container reset")
