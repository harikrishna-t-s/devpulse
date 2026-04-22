"""Article fetching module for DevPulse.

This module orchestrates the fetching of articles from multiple sources:
- RSS/Atom feeds via RSSAdapter
- Web scraping via ScraperAdapter
- Parallel fetching using ThreadPoolExecutor
- Automatic scoring and storage of relevant articles

The fetcher follows this workflow:
1. Clear existing articles (freshness-first approach)
2. Fetch from all configured RSS and scraping sources in parallel
3. Score each article using the configured scorer
4. Store articles that meet the relevance threshold

Example:
    fetcher = ArticleFetcher(storage, scorer)
    count = fetcher.fetch_all(topic='kubernetes')
    print(f"Fetched {count} articles")
"""

import concurrent.futures
from typing import Optional
from devpulse.core.adapters.rss import RSSAdapter, ScraperAdapter
from devpulse.core.logging_config import get_logger

logger = get_logger(__name__)


class ArticleFetcher:
    """Fetches articles from RSS and scraping sources in parallel.
    
    This class orchestrates content aggregation from multiple sources:
    - RSS/Atom feeds for structured content
    - Web scraping for sites without feeds
    - Parallel processing for efficiency
    - Automatic scoring and filtering
    
    Attributes:
        storage: Storage instance for persisting articles
        scorer: Scorer instance for relevance calculation
        rss_adapter: Adapter for RSS/Atom feeds
        scraper_adapter: Adapter for web scraping
    
    Example:
        >>> fetcher = ArticleFetcher(storage, scorer)
        >>> count = fetcher.fetch_all(topic='kubernetes')
        >>> print(f"Fetched {count} articles")
    """
    
    def __init__(self, storage, scorer) -> None:
        """Initialize the article fetcher.
        
        Args:
            storage: Storage instance for persisting articles
            scorer: Scorer instance for relevance calculation
        """
        self.storage = storage
        self.scorer = scorer
        self.rss_adapter = RSSAdapter()
        self.scraper_adapter = ScraperAdapter()

    def fetch_all(self, topic: Optional[str] = None) -> int:
        """Fetch articles from all configured sources.
        
        This method:
        1. Clears existing articles (freshness-first approach)
        2. Fetches from all RSS and scraping sources in parallel
        3. Scores each article
        4. Stores articles meeting the relevance threshold
        
        Args:
            topic: Optional topic to filter and weight articles by
        
        Returns:
            Total number of articles fetched and stored.
        
        Example:
            >>> fetcher.fetch_all(topic='kubernetes')
            87
        """
        from devpulse.config import config
        
        try:
            # Wipe previous data before each fetch to ensure freshness
            self.storage.clear_articles()
            
            sources = config.get('sources', {})
            total_count = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                
                # RSS Sources
                for src in sources.get('rss', []):
                    futures.append(executor.submit(self._fetch_source, src, self.rss_adapter, topic))
                
                # Scraping Sources
                for src in sources.get('scraping', []):
                    futures.append(executor.submit(self._fetch_source, src, self.scraper_adapter, topic))

                for future in concurrent.futures.as_completed(futures):
                    try:
                        count = future.result()
                        if count:
                            total_count += count
                    except Exception as e:
                        logger.warning(f"Worker thread error: {e}")

            logger.info(f"Fetched {total_count} articles total")
            return total_count
        except Exception as e:
            logger.error(f"Error during collective fetch: {e}", exc_info=True)
            return 0

    def _fetch_source(self, source: dict, adapter, topic: Optional[str] = None) -> int:
        """Fetch articles from a single source.
        
        Args:
            source: Source configuration dict with 'name' and 'url' keys
            adapter: Adapter instance (RSSAdapter or ScraperAdapter)
            topic: Optional topic to filter by
        
        Returns:
            Number of articles fetched and stored from this source.
        
        Note:
            Individual article errors are logged but don't stop processing
            of other articles from the same source.
        """
        try:
            raw_articles = adapter.fetch(source['url'])
            if not raw_articles:
                return 0
                
            count = 0
            for art in raw_articles:
                try:
                    score = self.scorer.calculate_score(art, topic)
                    if self.scorer.is_relevant(score):
                        self.storage.add_article(
                            art['title'], 
                            art['url'], 
                            source['name'], 
                            score, 
                            art['content']
                        )
                        count += 1
                except Exception as art_err:
                    logger.debug(f"Error processing article from {source['name']}: {art_err}")
                    continue
            logger.debug(f"Fetched {count} articles from {source['name']}")
            return count
        except Exception as e:
            logger.warning(f"Error fetching from {source.get('name', 'unknown')}: {e}")
            return 0
