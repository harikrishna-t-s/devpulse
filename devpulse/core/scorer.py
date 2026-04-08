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

        return score

    def is_relevant(self, score):
        return score >= self.threshold

scorer = Scorer()
