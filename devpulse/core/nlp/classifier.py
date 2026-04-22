from pathlib import Path
from typing import List, Tuple
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from devpulse.config import config


class TextClassifier:
    def __init__(self):
        self.model_path = Path.home() / '.devpulse' / config.get('nlp.model_path', 'models')
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        self.model_file = self.model_path / 'classifier.joblib'
        self.pipeline = None
        
        # Load model if exists
        if self.model_file.exists():
            self.load_model()
            
    def create_pipeline(self):
        """Create the classification pipeline."""
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(stop_words='english', max_features=1000)),
            ('classifier', MultinomialNB())
        ])
        
    def train(self, positive_samples: List[str], negative_samples: List[str]):
        """Train the classifier with positive and negative samples."""
        if not positive_samples or not negative_samples:
            raise ValueError("Both positive and negative samples are required")
            
        # Prepare training data
        X = positive_samples + negative_samples
        y = [1] * len(positive_samples) + [0] * len(negative_samples)
        
        # Create and train pipeline
        self.create_pipeline()
        self.pipeline.fit(X, y)
        
        # Save model
        self.save_model()
        
    def predict(self, text: str) -> Tuple[int, float]:
        """Predict if text is DevOps-relevant. Returns (label, probability)."""
        if self.pipeline is None:
            # Return neutral if no model is trained
            return 1, 0.5
            
        try:
            proba = self.pipeline.predict_proba([text])[0]
            label = int(proba[1] > 0.5)
            confidence = float(proba[1])
            return label, confidence
        except Exception:
            return 1, 0.5
            
    def load_model(self):
        """Load trained model from disk."""
        try:
            self.pipeline = joblib.load(self.model_file)
        except Exception:
            self.pipeline = None
            
    def save_model(self):
        """Save trained model to disk."""
        if self.pipeline is not None:
            joblib.dump(self.pipeline, self.model_file)
            
    def is_model_trained(self) -> bool:
        """Check if a trained model exists."""
        return self.model_file.exists() and self.pipeline is not None


classifier = TextClassifier()
