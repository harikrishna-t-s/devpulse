"""Content adapters module for DevPulse.

This module provides adapters for fetching content from various sources:
- RSS/Atom feeds via RSSAdapter
- Web scraping via ScraperAdapter
- Base adapter interface for extensibility

Adapters normalize content into a consistent article format
with title, url, content, and published date.

Example:
    adapter = RSSAdapter()
    articles = adapter.fetch('https://example.com/feed.xml')
"""

import feedparser
from typing import List, Dict, Any
from devpulse.utils.networking import fetch_url
from bs4 import BeautifulSoup
from devpulse.core.logging_config import get_logger

logger = get_logger(__name__)


class BaseAdapter:
    """Base adapter for content sources.
    
    Defines the interface that all content adapters must implement.
    Subclasses should override the fetch method to provide
    source-specific fetching logic.
    """
    
    def fetch(self, url: str) -> List[Dict[str, Any]]:
        """Fetch content from a URL.
        
        Args:
            url: URL to fetch content from
        
        Returns:
            List of article dictionaries with keys:
            - title: Article title
            - url: Article URL
            - content: Article content/body
            - published: Publication date (optional)
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError


class RSSAdapter(BaseAdapter):
    """Adapter for RSS/Atom feeds.
    
    Parses RSS and Atom feeds using feedparser and extracts
    article information including title, link, summary, and
    publication date.
    
    Example:
        >>> adapter = RSSAdapter()
        >>> articles = adapter.fetch('https://kubernetes.io/feed.xml')
        >>> print(len(articles))
        10
    """
    
    def fetch(self, url: str) -> List[Dict[str, Any]]:
        """Parse RSS/Atom feed and return articles.
        
        Args:
            url: RSS/Atom feed URL
        
        Returns:
            List of article dictionaries. Returns empty list on error.
        """
        try:
            feed = feedparser.parse(url)
            articles = []
            for entry in feed.entries:
                articles.append({
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'content': entry.get('summary', '') or entry.get('description', ''),
                    'published': entry.get('published', '')
                })
            logger.debug(f"Fetched {len(articles)} articles from RSS feed")
            return articles
        except Exception as e:
            logger.warning(f"Error parsing RSS feed {url}: {e}")
            return []

class ScraperAdapter(BaseAdapter):
    """Adapter for web scraping.
    
    Scrapes content from websites that don't provide RSS feeds.
    Currently supports:
    - GitHub Trending repositories
    - GitHub Topics pages
    
    Uses BeautifulSoup for HTML parsing and custom selectors
    for each supported site.
    
    Example:
        >>> adapter = ScraperAdapter()
        >>> articles = adapter.fetch('https://github.com/trending')
        >>> print(len(articles))
        25
    """
    
    def fetch(self, url: str) -> List[Dict[str, Any]]:
        """Scrape content from a URL.
        
        Args:
            url: URL to scrape
        
        Returns:
            List of article dictionaries. Returns empty list on error.
        
        Note:
            Only supports specific URLs (GitHub trending, GitHub topics).
            Other URLs will return empty list.
        """
        html = fetch_url(url)
        if not html:
            return []
        
        articles = []
        soup = BeautifulSoup(html, 'html.parser')
        
        if "github.com/trending" in url:
            # Scrape GitHub Trending repositories
            for repo in soup.select('article.Box-row'):
                title_elem = repo.select_one('h2 a')
                if not title_elem:
                    continue
                title = title_elem.text.strip().replace('\n', '').replace(' ', '')
                link = "https://github.com" + title_elem['href']
                desc = repo.select_one('p').text.strip() if repo.select_one('p') else ""
                articles.append({
                    'title': title,
                    'url': link,
                    'content': desc,
                    'published': None
                })
        elif "github.com/topics/devops" in url:
            # Scrape GitHub DevOps topic page
            for repo in soup.select('article.border'):
                title_elem = repo.select_one('h3 a.text-bold')
                if not title_elem:
                    continue
                link = "https://github.com" + title_elem['href']
                title = title_elem.text.strip()
                desc = repo.select_one('div.color-fg-muted').text.strip() if repo.select_one('div.color-fg-muted') else ""
                articles.append({
                    'title': title,
                    'url': link,
                    'content': desc,
                    'published': None
                })
        
        logger.debug(f"Scraped {len(articles)} articles from {url}")
        return articles
