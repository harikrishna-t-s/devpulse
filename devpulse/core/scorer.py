import re
from datetime import datetime
from devpulse.config import config
from devpulse.core.nlp.engine import nlp_engine
from devpulse.core.nlp.classifier import classifier
from devpulse.core.nlp.ner import ner_engine

class Scorer:
    def __init__(self):
        self.weights = config.get('scoring.weights', {})
        self.threshold = config.get('scoring.threshold', 50)
        self.freshness_boost = config.get('scoring.freshness_boost', 20)
        self.nlp_enabled = config.get('nlp.enabled', True)

    def calculate_score(self, article, topic=None):
        score = 0
        title = article.get('title', '').lower()
        content = article.get('content', '').lower()
        text = title + " " + content
        
        # Mandatory Topic Match: If a topic is specified, it MUST be present.
        if topic:
            topic_lower = topic.lower()
            if topic_lower not in text:
                return 0 # Skip articles that don't mention the topic at all
            
            # Heavy weighting for the specific topic
            title_topic_count = title.count(topic_lower)
            content_topic_count = content.count(topic_lower)
            score += (title_topic_count * 100) + (content_topic_count * 50)

        # General Keyword based scoring (secondary to the topic)
        for kw, weight in self.weights.items():
            kw_lower = kw.lower()
            if kw_lower in text:
                # Count occurrences
                title_matches = title.count(kw_lower)
                content_matches = content.count(kw_lower)
                
                # Title matches are weighted 3x
                score += (title_matches * weight * 2)
                # Content matches are weighted 1x
                score += (content_matches * weight)

        # Freshness boost
        if article.get('published'):
            score += self.freshness_boost

        # NLP-based scoring
        if self.nlp_enabled:
            score += self._add_nlp_scores(article)

        return score

    def _add_nlp_scores(self, article) -> float:
        """Add NLP-based scores to the base score."""
        nlp_score = 0.0
        text = f"{article.get('title', '')} {article.get('content', '')}"

        try:
            # TF-IDF score
            if config.get('nlp.components.tfidf.enabled', True):
                nlp_score += nlp_engine.compute_tfidf_score(text) * config.get('nlp.components.tfidf.weight', 0.3)

            # Cosine similarity score
            if config.get('nlp.components.cosine_similarity.enabled', True):
                nlp_score += nlp_engine.compute_cosine_similarity_score(text) * config.get('nlp.components.cosine_similarity.weight', 0.2)

            # RAKE score
            if config.get('nlp.components.rake.enabled', True):
                nlp_score += nlp_engine.compute_rake_score(text) * config.get('nlp.components.rake.weight', 0.15)

            # Classifier score
            if config.get('nlp.components.classifier.enabled', True) and classifier.is_model_trained():
                _, confidence = classifier.predict(text)
                nlp_score += confidence * 100 * config.get('nlp.components.classifier.weight', 0.2)

            # NER score
            if config.get('nlp.components.ner.enabled', True):
                nlp_score += ner_engine.compute_ner_score(text) * config.get('nlp.components.ner.weight', 0.15)
        except Exception:
            # Fallback to base scoring if NLP fails
            pass

        return nlp_score

    def is_relevant(self, score):
        return score >= self.threshold

scorer = Scorer()
