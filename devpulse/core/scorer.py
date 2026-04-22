"""Article scoring module for DevPulse.

This module provides relevance scoring for articles using a combination of:
- Keyword-based scoring with configurable weights
- Topic-specific filtering and weighting
- NLP-based semantic analysis (TF-IDF, cosine similarity, RAKE)
- Machine learning classification (Naive Bayes)
- Named Entity Recognition (NER)

The scoring pipeline follows this order:
1. Topic filtering (if topic specified) - articles without topic are rejected
2. Topic weighting - heavy boost for topic occurrences in title/content
3. Keyword scoring - weighted sum of keyword matches
4. Freshness boost - additional score for recently published articles
5. NLP scoring - optional semantic and entity-based scoring

Example:
    scorer = ArticleScorer()
    article = {'title': 'Kubernetes deployment', 'content': '...', 'published': '2024-01-01'}
    score = scorer.calculate_score(article, topic='kubernetes')
    if scorer.is_relevant(score):
        # Article is relevant
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any
from devpulse.config import config
from devpulse.core.logging_config import get_logger
from devpulse.core.topic_filter import TopicFilter

logger = get_logger(__name__)


class ArticleScorer:
    """Article scorer combining keyword-based and NLP-based scoring.
    
    This class calculates relevance scores for articles based on:
    - Configurable keyword weights from config.yaml
    - Topic-specific filtering and weighting
    - Optional NLP-based semantic analysis
    
    Attributes:
        weights: Dictionary of keyword weights from configuration
        threshold: Minimum score for an article to be considered relevant
        freshness_boost: Additional score for recently published articles
        nlp_enabled: Whether NLP scoring is enabled
        topic_filter: TopicFilter instance for topic validation
    
    Example:
        scorer = ArticleScorer()
        score = scorer.calculate_score(article, topic='kubernetes')
    """
    
    def __init__(self, topic_filter: Optional[TopicFilter] = None) -> None:
        """Initialize the article scorer.
        
        Args:
            topic_filter: Optional TopicFilter instance. If None, creates a new one.
        """
        self.weights = config.get('scoring.weights', {})
        self.threshold = config.get('scoring.threshold', 50)
        self.freshness_boost = config.get('scoring.freshness_boost', 20)
        self.nlp_enabled = config.get('nlp.enabled', True)
        self.topic_filter = topic_filter or TopicFilter()
        
        # Lazy-load NLP components to improve startup time
        self._nlp_engine = None
        self._classifier = None
        self._ner_engine = None

    def _get_nlp_engine(self) -> Optional[Any]:
        """Lazy-load the NLP engine.
        
        Returns:
            NLPEngine instance if enabled and NLP is available, None otherwise.
        """
        if self._nlp_engine is None and self.nlp_enabled:
            from devpulse.core.nlp.engine import NLPEngine
            self._nlp_engine = NLPEngine()
            logger.debug("NLP engine lazy-loaded")
        return self._nlp_engine
    
    def _get_classifier(self) -> Optional[Any]:
        """Lazy-load the text classifier.
        
        Returns:
            TextClassifier instance if enabled and available, None otherwise.
        """
        if self._classifier is None and self.nlp_enabled:
            from devpulse.core.nlp.classifier import TextClassifier
            self._classifier = TextClassifier()
            logger.debug("Classifier lazy-loaded")
        return self._classifier
    
    def _get_ner_engine(self) -> Optional[Any]:
        """Lazy-load the NER engine.
        
        Returns:
            NEREngine instance if enabled and available, None otherwise.
        """
        if self._ner_engine is None and self.nlp_enabled:
            from devpulse.core.nlp.ner import NEREngine
            self._ner_engine = NEREngine()
            logger.debug("NER engine lazy-loaded")
        return self._ner_engine
    
    def calculate_score(self, article: Dict[str, Any], topic: Optional[str] = None) -> float:
        """Calculate relevance score for an article.
        
        The scoring algorithm:
        1. Filters out articles that don't contain the specified topic (if any)
        2. Applies heavy weighting for topic occurrences (100x in title, 50x in content)
        3. Scores based on keyword matches (2x weight in title, 1x in content)
        4. Adds freshness boost for recently published articles
        5. Adds NLP-based semantic scores if enabled
        
        Args:
            article: Dictionary containing article data with keys:
                - title: Article title
                - content: Article content/body
                - published: Optional publication date
            topic: Optional topic string to filter and weight by
        
        Returns:
            Relevance score as a float. Returns 0.0 if article doesn't match topic.
        
        Example:
            >>> article = {'title': 'Kubernetes guide', 'content': 'Learn k8s', 'published': '2024-01-01'}
            >>> score = scorer.calculate_score(article, topic='kubernetes')
            >>> print(score)
            150.0
        """
        # Topic filtering - separate concern
        if not self.topic_filter.is_valid(article, topic):
            return 0.0
        
        score: float = 0.0
        title = article.get('title', '').lower()
        content = article.get('content', '').lower()
        text = title + " " + content
        
        # Topic weighting (if topic is specified)
        if topic:
            topic_lower = topic.lower()
            title_topic_count = title.count(topic_lower)
            content_topic_count = content.count(topic_lower)
            score += (title_topic_count * 100) + (content_topic_count * 50)

        # General Keyword based scoring
        for kw, weight in self.weights.items():
            kw_lower = kw.lower()
            if kw_lower in text:
                title_matches = title.count(kw_lower)
                content_matches = content.count(kw_lower)
                score += (title_matches * weight * 2)
                score += (content_matches * weight)

        # Freshness boost
        if article.get('published'):
            score += self.freshness_boost

        # NLP-based scoring
        if self.nlp_enabled:
            score += self._add_nlp_scores(article)

        return score

    def _add_nlp_scores(self, article: Dict[str, Any]) -> float:
        """Add NLP-based scores to the base score.
        
        This method combines multiple NLP techniques:
        - Semantic similarity (TF-IDF + Cosine Similarity)
        - Naive Bayes classification confidence
        - Named Entity Recognition (NER) matches
        
        Args:
            article: Article dictionary with title and content
        
        Returns:
            Weighted NLP score as a float. Returns 0.0 if NLP fails or is disabled.
        """
        nlp_score: float = 0.0
        text = f"{article.get('title', '')} {article.get('content', '')}"

        try:
            nlp_engine = self._get_nlp_engine()
            if nlp_engine is None:
                return 0.0
            
            # Semantic score (combined TF-IDF + Cosine Similarity)
            nlp_score += nlp_engine.get_weighted_nlp_score(article)

            # Classifier score
            classifier = self._get_classifier()
            if config.get('nlp.components.classifier.enabled', True) and classifier and classifier.is_model_trained():
                _, confidence = classifier.predict(text)
                nlp_score += confidence * 100 * config.get('nlp.components.classifier.weight', 0.2)

            # NER score
            ner_engine = self._get_ner_engine()
            if config.get('nlp.components.ner.enabled', True) and ner_engine:
                nlp_score += ner_engine.compute_ner_score(text) * config.get('nlp.components.ner.weight', 0.15)
        except Exception as e:
            logger.warning(f"NLP scoring failed, using base score only: {e}")

        return nlp_score

    def is_relevant(self, score: float) -> bool:
        """Check if score meets relevance threshold.
        
        Args:
            score: The calculated relevance score
        
        Returns:
            True if score >= threshold, False otherwise
        
        Example:
            >>> scorer.is_relevant(75)
            True
            >>> scorer.is_relevant(25)
            False
        """
        return score >= self.threshold
