"""Topic filtering module for DevPulse.

This module provides topic-based filtering for articles.
It validates that articles contain the specified topic
before scoring and storage.

Example:
    filter = TopicFilter()
    article = {'title': 'Kubernetes guide', 'content': 'Learn k8s'}
    if filter.is_valid(article, topic='kubernetes'):
        # Article is relevant
"""

from typing import Optional, Dict, Any
from devpulse.core.logging_config import get_logger

logger = get_logger(__name__)


class TopicFilter:
    """Filters articles based on topic presence.
    
    This class implements the Single Responsibility Principle by
    handling only topic validation logic, separating it from scoring.
    
    Example:
        >>> filter = TopicFilter()
        >>> article = {'title': 'Kubernetes guide', 'content': 'Learn k8s'}
        >>> filter.is_valid(article, topic='kubernetes')
        True
    """
    
    def is_valid(self, article: Dict[str, Any], topic: Optional[str] = None) -> bool:
        """Check if article is valid for the given topic.
        
        Validates that the article contains the specified topic
        in either the title or content. If no topic is specified,
        all articles are considered valid.
        
        Args:
            article: Article dictionary with title and content keys
            topic: Optional topic string to filter by
        
        Returns:
            True if article contains the topic or no topic specified,
            False otherwise.
        
        Example:
            >>> filter.is_valid({'title': 'K8s guide'}, topic='kubernetes')
            False
            >>> filter.is_valid({'title': 'Kubernetes guide'}, topic='kubernetes')
            True
        """
        if not topic:
            return True
        
        topic_lower = topic.lower()
        text = f"{article.get('title', '')} {article.get('content', '')}".lower()
        
        is_valid = topic_lower in text
        if not is_valid:
            logger.debug(f"Article filtered out: topic '{topic}' not found")
        
        return is_valid
