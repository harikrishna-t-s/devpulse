import re
from datetime import datetime
from devpulse.config import config

class Scorer:
    def __init__(self):
        self.weights = config.get('scoring.weights', {})
        self.threshold = config.get('scoring.threshold', 50)
        self.freshness_boost = config.get('scoring.freshness_boost', 20)

    def calculate_score(self, article, topic=None):
        score = 0
        text = (article['title'] + " " + article['content']).lower()
        
        # Keyword based scoring
        for kw, weight in self.weights.items():
            if kw.lower() in text:
                # Give more weight if keyword is in title
                if kw.lower() in article['title'].lower():
                    score += weight * 2
                else:
                    score += weight

        # Topic specific boost
        if topic and topic.lower() in text:
            score += 30

        # Freshness boost (if published date is available)
        if article.get('published'):
            # Basic freshness boost for now
            score += self.freshness_boost

        # Reputation boost (placeholder for future implementation)
        # score += source_reputation.get(article['source'], 0)

        return score

    def is_relevant(self, score):
        return score >= self.threshold

scorer = Scorer()
