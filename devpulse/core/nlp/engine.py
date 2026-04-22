"""NLP engine module for semantic analysis and scoring.

This module provides natural language processing capabilities for DevPulse:
- TF-IDF vectorization for keyword-based similarity
- Cosine similarity for semantic matching against curated corpus
- RAKE (Rapid Automatic Keyword Extraction) for keyword extraction
- Combined semantic scoring using multiple techniques

The engine uses lazy initialization to improve startup time.
Components are only loaded when first used.

Example:
    engine = NLPEngine()
    semantic_score = engine.compute_semantic_score('Kubernetes deployment guide')
    rake_score = engine.compute_rake_score('Docker container orchestration')
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import joblib
import numpy as np
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rake_nltk import Rake
from devpulse.config import config
from devpulse.core.logging_config import get_logger

logger = get_logger(__name__)

# Download required NLTK resources
try:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
except Exception as e:
    logger.warning(f"Failed to download NLTK resources: {e}")


class NLPEngine:
    """NLP engine for semantic analysis and scoring.
    
    This class provides multiple NLP techniques for article relevance scoring:
    - TF-IDF similarity against DevOps keywords
    - Cosine similarity against curated corpus
    - RAKE keyword extraction
    - Combined weighted scoring
    
    All components use lazy initialization for performance.
    
    Attributes:
        enabled: Whether NLP scoring is enabled
        settings: NLP configuration settings
        weights: Component weights for scoring
        model_path: Path to store/load models
        corpus_path: Path to curated corpus files
        devops_keywords: List of DevOps-related keywords
    
    Example:
        >>> engine = NLPEngine()
        >>> score = engine.compute_semantic_score('Kubernetes deployment guide')
        >>> print(f"Semantic score: {score:.2f}")
    """
    
    def __init__(self) -> None:
        """Initialize the NLP engine.
        
        Sets up paths, directories, and keyword corpus.
        Components are lazy-loaded on first use.
        """
        self.enabled = config.get('nlp.enabled', True)
        self.settings = config.get('nlp.settings', {})
        self.weights = config.get('nlp.components', {})
        
        # Paths
        self.model_path = Path.home() / '.devpulse' / config.get('nlp.model_path', 'models')
        self.corpus_path = Path.home() / '.devpulse' / config.get('nlp.corpus_path', 'corpus')
        
        # Ensure directories exist
        self.model_path.mkdir(parents=True, exist_ok=True)
        self.corpus_path.mkdir(parents=True, exist_ok=True)
        
        # DevOps keyword corpus for TF-IDF similarity
        self.devops_keywords = [
            'kubernetes', 'docker', 'terraform', 'ansible', 'ci/cd',
            'continuous integration', 'continuous deployment', 'devops',
            'infrastructure as code', 'gitops', 'observability',
            'prometheus', 'grafana', 'monitoring', 'logging',
            'serverless', 'cloud native', 'microservices',
            'container orchestration', 'helm', 'jenkins',
            'aws', 'azure', 'gcp', 'security', 'sre',
            'site reliability engineering', 'chaos engineering',
            'blue green deployment', 'canary release'
        ]
        
        # Lazy initialization flags
        self._tfidf_initialized = False
        self._rake_initialized = False
        self._curated_loaded = False
        
        # Component storage
        self.tfidf_vectorizer = None
        self.rake = None
        self.curated_samples = []
        
    def _init_tfidf(self) -> None:
        """Initialize TF-IDF vectorizer with n-gram support.
        
        Creates a TfidfVectorizer fitted on DevOps keywords for
        computing similarity scores against known DevOps terminology.
        Uses lazy initialization to defer expensive operations.
        """
        if self._tfidf_initialized:
            return
        ngram_range = tuple(self.settings.get('ngram_range', [2, 3]))
        self.tfidf_vectorizer = TfidfVectorizer(
            ngram_range=ngram_range,
            stop_words='english',
            max_features=1000
        )
        self.tfidf_vectorizer.fit([' '.join(self.devops_keywords)])
        self._tfidf_initialized = True
        logger.debug("TF-IDF vectorizer initialized")
        
    def _init_rake(self) -> None:
        """Initialize RAKE keyword extractor.
        
        RAKE (Rapid Automatic Keyword Extraction) identifies
        important phrases in text by analyzing word co-occurrence.
        """
        if self._rake_initialized:
            return
        self.rake = Rake()
        self._rake_initialized = True
        logger.debug("RAKE initialized")
        
    def _load_curated_corpus(self) -> None:
        """Load curated corpus for similarity comparison.
        
        Loads a curated corpus of high-quality DevOps articles
        from disk. Used for cosine similarity scoring to match
        new articles against known good content.
        """
        if self._curated_loaded:
            return
        corpus_file = self.corpus_path / 'curated.txt'
        if corpus_file.exists():
            with open(corpus_file, 'r', encoding='utf-8') as f:
                self.curated_samples = [line.strip() for line in f if line.strip()]
        else:
            self.curated_samples = []
        self._curated_loaded = True
        logger.debug(f"Loaded {len(self.curated_samples)} curated samples")
            
    def compute_semantic_score(self, text: str) -> float:
        """Combined semantic score using TF-IDF and corpus similarity.
        
        This method combines two semantic similarity approaches:
        1. TF-IDF similarity against DevOps keywords (terminology match)
        2. Cosine similarity against curated corpus (content quality match)
        
        The two scores are weighted according to configuration and averaged.
        
        Args:
            text: Text to analyze (typically article title + content)
        
        Returns:
            Combined semantic score (0-100). Returns 0.0 if disabled or error.
        
        Example:
            >>> engine.compute_semantic_score('Kubernetes deployment guide')
            45.23
        """
        if not (self.weights.get('tfidf.enabled', True) or self.weights.get('cosine_similarity.enabled', True)):
            return 0.0
            
        try:
            self._init_tfidf()
            self._load_curated_corpus()
            text_clean = self._preprocess(text)
            if not text_clean:
                return 0.0
                
            # TF-IDF similarity against DevOps keywords
            tfidf_score = 0.0
            if self.weights.get('tfidf.enabled', True):
                text_vector = self.tfidf_vectorizer.transform([text_clean])
                keyword_vector = self.tfidf_vectorizer.transform([' '.join(self.devops_keywords)])
                similarity = cosine_similarity(text_vector, keyword_vector)[0][0]
                tfidf_score = float(similarity * 100)
            
            # Cosine similarity against curated corpus
            corpus_score = 0.0
            if self.weights.get('cosine_similarity.enabled', True) and self.curated_samples:
                all_texts = self.curated_samples + [text_clean]
                vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
                tfidf_matrix = vectorizer.fit_transform(all_texts)
                text_vec = tfidf_matrix[-1]
                corpus_vecs = tfidf_matrix[:-1]
                similarities = cosine_similarity(text_vec, corpus_vecs)
                corpus_score = float(np.max(similarities) * 100)
            
            # Weighted average
            tfidf_weight = self.weights.get('tfidf.weight', 0.3)
            corpus_weight = self.weights.get('cosine_similarity.weight', 0.2)
            total_weight = tfidf_weight + corpus_weight
            if total_weight > 0:
                return (tfidf_score * tfidf_weight + corpus_score * corpus_weight) / total_weight
            return 0.0
        except Exception as e:
            logger.warning(f"Semantic scoring failed: {e}")
            return 0.0
            
    def compute_rake_score(self, text: str) -> float:
        """Compute RAKE keyword extraction score.
        
        RAKE extracts important phrases from text and scores them
        based on how many DevOps keywords they contain.
        
        Args:
            text: Text to analyze
        
        Returns:
            RAKE score (0-100) based on DevOps keyword matches.
        
        Example:
            >>> engine.compute_rake_score('Docker container orchestration')
            50.0
        """
        if not self.weights.get('rake.enabled', True):
            return 0.0
            
        try:
            self._init_rake()
            text_clean = self._preprocess(text, max_length=500)
            if not text_clean:
                return 0.0
                
            self.rake.extract_keywords_from_text(text_clean)
            keywords = self.rake.get_ranked_phrases()
            
            # Count how many extracted phrases contain DevOps keywords
            matches = 0
            for kw in keywords:
                for devops_kw in self.devops_keywords:
                    if devops_kw in kw.lower():
                        matches += 1
                        
            max_possible = len(keywords) if keywords else 1
            return float((matches / max_possible) * 100)
        except Exception as e:
            logger.warning(f"RAKE scoring failed: {e}")
            return 0.0
            
    def _preprocess(self, text: str, max_length: Optional[int] = None) -> str:
        """Preprocess text for NLP operations.
        
        Performs the following transformations:
        - Removes HTML tags
        - Removes punctuation
        - Converts to lowercase
        - Normalizes whitespace
        - Optionally truncates to max_length words
        
        Args:
            text: Raw text to preprocess
            max_length: Optional maximum number of words to keep
        
        Returns:
            Preprocessed text string.
        """
        if not text:
            return ""
            
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = text.lower()
        text = ' '.join(text.split())
        
        if max_length:
            words = text.split()
            text = ' '.join(words[:max_length])
            
        return text
        
    def compute_nlp_scores(self, article: Dict[str, Any]) -> Dict[str, float]:
        """Compute all NLP scores for an article.
        
        Args:
            article: Article dictionary with title and content
        
        Returns:
            Dictionary of NLP scores with keys:
            - semantic: Combined TF-IDF + cosine similarity score
            - rake: RAKE keyword extraction score
        
        Example:
            >>> engine.compute_nlp_scores({'title': 'K8s', 'content': '...'})
            {'semantic': 45.23, 'rake': 30.0}
        """
        if not self.enabled:
            return {}
            
        text = f"{article.get('title', '')} {article.get('content', '')}"
        
        scores = {
            'semantic': self.compute_semantic_score(text),
            'rake': self.compute_rake_score(text)
        }
        
        return scores
        
    def get_weighted_nlp_score(self, article: Dict[str, Any]) -> float:
        """Compute weighted NLP score.
        
        Combines all NLP scores using configured weights.
        
        Args:
            article: Article dictionary with title and content
        
        Returns:
            Weighted sum of all enabled NLP scores.
        
        Example:
            >>> engine.get_weighted_nlp_score({'title': 'K8s', 'content': '...'})
            25.5
        """
        if not self.enabled:
            return 0.0
            
        scores = self.compute_nlp_scores(article)
        weighted_sum = 0.0
        
        # Semantic score (combined TF-IDF + Cosine)
        semantic_weight = self.weights.get('tfidf.weight', 0.3) + self.weights.get('cosine_similarity.weight', 0.2)
        if semantic_weight > 0:
            weighted_sum += scores.get('semantic', 0.0) * semantic_weight
        
        # RAKE score
        rake_weight = self.weights.get('rake.weight', 0.15)
        if rake_weight > 0:
            weighted_sum += scores.get('rake', 0.0) * rake_weight
                
        return weighted_sum
