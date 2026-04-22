import re
from pathlib import Path
from typing import Dict, List, Optional
import joblib
import numpy as np
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rake_nltk import Rake
from devpulse.config import config

# Download required NLTK resources
try:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
except Exception:
    pass


class NLPEngine:
    def __init__(self):
        self.enabled = config.get('nlp.enabled', True)
        self.settings = config.get('nlp.settings', {})
        self.weights = config.get('nlp.components', {})
        
        # Paths
        self.model_path = Path.home() / '.devpulse' / config.get('nlp.model_path', 'models')
        self.corpus_path = Path.home() / '.devpulse' / config.get('nlp.corpus_path', 'corpus')
        
        # Ensure directories exist
        self.model_path.mkdir(parents=True, exist_ok=True)
        self.corpus_path.mkdir(parents=True, exist_ok=True)
        
        # DevOps keyword corpus
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
        
        # Initialize components
        self._init_tfidf()
        self._init_rake()
        self._load_curated_corpus()
        
    def _init_tfidf(self):
        """Initialize TF-IDF vectorizer with n-gram support."""
        ngram_range = tuple(self.settings.get('ngram_range', [2, 3]))
        self.tfidf_vectorizer = TfidfVectorizer(
            ngram_range=ngram_range,
            stop_words='english',
            max_features=1000
        )
        self.tfidf_vectorizer.fit([' '.join(self.devops_keywords)])
        
    def _init_rake(self):
        """Initialize RAKE keyword extractor."""
        self.rake = Rake()
        
    def _load_curated_corpus(self):
        """Load curated corpus for similarity comparison."""
        corpus_file = self.corpus_path / 'curated.txt'
        if corpus_file.exists():
            with open(corpus_file, 'r', encoding='utf-8') as f:
                self.curated_samples = [line.strip() for line in f if line.strip()]
        else:
            self.curated_samples = []
            
    def compute_tfidf_score(self, text: str) -> float:
        """Compute TF-IDF similarity score against DevOps keywords."""
        if not self.weights.get('tfidf.enabled', True):
            return 0.0
            
        try:
            text_clean = self._preprocess(text)
            if not text_clean:
                return 0.0
                
            # Transform text
            text_vector = self.tfidf_vectorizer.transform([text_clean])
            keyword_vector = self.tfidf_vectorizer.transform([' '.join(self.devops_keywords)])
            
            # Compute similarity
            similarity = cosine_similarity(text_vector, keyword_vector)[0][0]
            return float(similarity * 100)
        except Exception:
            return 0.0
            
    def compute_cosine_similarity_score(self, text: str) -> float:
        """Compute cosine similarity against curated corpus."""
        if not self.weights.get('cosine_similarity.enabled', True) or not self.curated_samples:
            return 0.0
            
        try:
            text_clean = self._preprocess(text)
            if not text_clean:
                return 0.0
                
            # Fit vectorizer on corpus + new text
            all_texts = self.curated_samples + [text_clean]
            vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            
            # Get similarity with corpus samples
            text_vec = tfidf_matrix[-1]
            corpus_vecs = tfidf_matrix[:-1]
            similarities = cosine_similarity(text_vec, corpus_vecs)
            
            # Return max similarity
            return float(np.max(similarities) * 100)
        except Exception:
            return 0.0
            
    def compute_rake_score(self, text: str) -> float:
        """Compute RAKE keyword extraction score."""
        if not self.weights.get('rake.enabled', True):
            return 0.0
            
        try:
            text_clean = self._preprocess(text, max_length=500)
            if not text_clean:
                return 0.0
                
            self.rake.extract_keywords_from_text(text_clean)
            keywords = self.rake.get_ranked_phrases()
            
            # Count matches with DevOps keywords
            matches = 0
            for kw in keywords:
                for devops_kw in self.devops_keywords:
                    if devops_kw in kw.lower():
                        matches += 1
                        
            # Normalize score
            max_possible = len(keywords) if keywords else 1
            return float((matches / max_possible) * 100)
        except Exception:
            return 0.0
            
    def _preprocess(self, text: str, max_length: Optional[int] = None) -> str:
        """Preprocess text for NLP operations."""
        if not text:
            return ""
            
        # Clean text
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = text.lower()
        text = ' '.join(text.split())
        
        # Truncate if needed
        if max_length:
            words = text.split()
            text = ' '.join(words[:max_length])
            
        return text
        
    def compute_nlp_scores(self, article: Dict) -> Dict[str, float]:
        """Compute all NLP scores for an article."""
        if not self.enabled:
            return {}
            
        text = f"{article.get('title', '')} {article.get('content', '')}"
        
        scores = {
            'tfidf': self.compute_tfidf_score(text),
            'cosine_similarity': self.compute_cosine_similarity_score(text),
            'rake': self.compute_rake_score(text)
        }
        
        return scores
        
    def get_weighted_nlp_score(self, article: Dict) -> float:
        """Compute weighted NLP score."""
        if not self.enabled:
            return 0.0
            
        scores = self.compute_nlp_scores(article)
        weighted_sum = 0.0
        
        for component, score in scores.items():
            weight = self.weights.get(f'{component}.weight', 0.0)
            enabled = self.weights.get(f'{component}.enabled', True)
            
            if enabled:
                weighted_sum += score * weight
                
        return weighted_sum


nlp_engine = NLPEngine()
