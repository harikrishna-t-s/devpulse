"""Naive Bayes text classifier module for DevPulse.

This module provides a machine learning classifier to determine
whether articles are DevOps-relevant. It uses:
- TF-IDF vectorization for text feature extraction
- Multinomial Naive Bayes for classification
- Joblib for model persistence

The classifier must be trained with positive (DevOps) and negative
(non-DevOps) samples before use.

Example:
    classifier = TextClassifier()
    classifier.train(positive_samples, negative_samples)
    label, confidence = classifier.predict('Kubernetes deployment guide')
"""

from pathlib import Path
from typing import List, Tuple, Optional
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from devpulse.config import config
from devpulse.core.logging_config import get_logger

logger = get_logger(__name__)


class TextClassifier:
    """Naive Bayes text classifier for DevOps relevance.
    
    This class implements a binary text classifier using:
    - TF-IDF vectorization for feature extraction
    - Multinomial Naive Bayes for classification
    - Model persistence via joblib
    
    The classifier distinguishes between DevOps-relevant and
    non-DevOps content based on training data.
    
    Attributes:
        model_path: Directory for storing model files
        model_file: Path to the classifier model file
        pipeline: Scikit-learn pipeline (vectorizer + classifier)
    
    Example:
        >>> classifier = TextClassifier()
        >>> classifier.train(['kubernetes guide'], ['cooking recipe'])
        >>> label, confidence = classifier.predict('Docker container')
        >>> print(f"Relevant: {label}, Confidence: {confidence}")
    """
    
    def __init__(self) -> None:
        """Initialize the text classifier.
        
        Sets up model paths and loads existing model if available.
        """
        self.model_path = Path.home() / '.devpulse' / config.get('nlp.model_path', 'models')
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        self.model_file = self.model_path / 'classifier.joblib'
        self.pipeline: Optional[Pipeline] = None
        
        if self.model_file.exists():
            self.load_model()
            
    def create_pipeline(self) -> None:
        """Create the classification pipeline.
        
        Creates a scikit-learn pipeline with:
        - TF-IDF vectorizer (max 1000 features, English stopwords)
        - Multinomial Naive Bayes classifier
        """
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(stop_words='english', max_features=1000)),
            ('classifier', MultinomialNB())
        ])
        
    def train(self, positive_samples: List[str], negative_samples: List[str]) -> None:
        """Train the classifier with positive and negative samples.
        
        Args:
            positive_samples: List of DevOps-relevant text samples
            negative_samples: List of non-DevOps text samples
        
        Raises:
            ValueError: If either sample list is empty
        
        Example:
            >>> classifier.train(
            ...     ['kubernetes deployment', 'docker containers'],
            ...     ['cooking recipes', 'sports news']
            ... )
        """
        if not positive_samples or not negative_samples:
            raise ValueError("Both positive and negative samples are required")
            
        X = positive_samples + negative_samples
        y = [1] * len(positive_samples) + [0] * len(negative_samples)
        
        self.create_pipeline()
        self.pipeline.fit(X, y)
        self.save_model()
        logger.info(f"Trained classifier with {len(positive_samples)} positive and {len(negative_samples)} negative samples")
        
    def predict(self, text: str) -> Tuple[int, float]:
        """Predict if text is DevOps-relevant.
        
        Args:
            text: Text to classify
        
        Returns:
            Tuple of (label, confidence) where:
            - label: 1 for DevOps-relevant, 0 for not relevant
            - confidence: Probability of being DevOps-relevant (0-1)
        
        Note:
            Returns (1, 0.5) if model is not trained.
        
        Example:
            >>> classifier.predict('Kubernetes deployment guide')
            (1, 0.95)
        """
        if self.pipeline is None:
            return 1, 0.5
            
        try:
            proba = self.pipeline.predict_proba([text])[0]
            label = int(proba[1] > 0.5)
            confidence = float(proba[1])
            return label, confidence
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            return 1, 0.5
            
    def load_model(self) -> None:
        """Load trained model from disk.
        
        Loads the classifier model from the model file if it exists.
        Sets pipeline to None if loading fails.
        """
        try:
            self.pipeline = joblib.load(self.model_file)
            logger.debug("Classifier model loaded")
        except Exception as e:
            logger.warning(f"Failed to load classifier model: {e}")
            self.pipeline = None
            
    def save_model(self) -> None:
        """Save trained model to disk.
        
        Persists the trained pipeline to disk using joblib.
        """
        if self.pipeline is not None:
            joblib.dump(self.pipeline, self.model_file)
            logger.debug("Classifier model saved")
            
    def is_model_trained(self) -> bool:
        """Check if a trained model exists.
        
        Returns:
            True if model file exists and pipeline is loaded, False otherwise.
        """
        return self.model_file.exists() and self.pipeline is not None
