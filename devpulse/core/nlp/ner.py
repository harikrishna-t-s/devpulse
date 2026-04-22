"""Named Entity Recognition module for DevPulse.

This module provides NER capabilities using spaCy to identify
DevOps-related entities in text. It:
- Uses spaCy's en_core_web_sm model for efficiency
- Filters entities against a DevOps whitelist
- Scores articles based on entity matches

Example:
    ner = NEREngine()
    entities = ner.extract_entities('Kubernetes and Docker deployment')
    score = ner.compute_ner_score('AWS Lambda functions')
"""

from pathlib import Path
from typing import Set, Optional
import spacy
from devpulse.config import config
from devpulse.core.logging_config import get_logger

logger = get_logger(__name__)


class NEREngine:
    """Named Entity Recognition engine for DevOps entities.
    
    This class uses spaCy to extract named entities from text
    and filters them against a whitelist of known DevOps tools,
    platforms, and technologies.
    
    Attributes:
        enabled: Whether NER scoring is enabled
        model_path: Path to spaCy model directory
        devops_entities: Set of DevOps-related entity names
        nlp: spaCy language model (loaded on init)
    
    Example:
        >>> ner = NEREngine()
        >>> entities = ner.extract_entities('Kubernetes deployment on AWS')
        >>> print(entities)
        {'kubernetes', 'aws'}
    """
    
    def __init__(self) -> None:
        """Initialize the NER engine.
        
        Loads the spaCy model and sets up the DevOps entity whitelist.
        """
        self.enabled = config.get('nlp.components.ner.enabled', True)
        self.model_path = Path.home() / '.devpulse' / config.get('nlp.model_path', 'models')
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # Whitelist of DevOps-related entities to recognize
        self.devops_entities = {
            'kubernetes', 'docker', 'terraform', 'ansible', 'jenkins',
            'prometheus', 'grafana', 'aws', 'azure', 'gcp', 'heroku',
            'kafka', 'redis', 'postgresql', 'mysql', 'mongodb',
            'nginx', 'apache', 'gitlab', 'github', 'bitbucket',
            'jira', 'confluence', 'slack', 'mattermost',
            'vault', 'consul', 'nomad', 'etcd', 'flannel',
            'calico', 'istio', 'envoy', 'linkerd', 'helm',
            'argocd', 'flux', 'tekton', 'spinnaker', 'knative'
        }
        
        self.nlp: Optional[spacy.Language] = None
        self._load_model()
        
    def _load_model(self) -> None:
        """Load spaCy small model for efficiency.
        
        Loads the en_core_web_sm model with parser and lemmatizer
        disabled for faster processing since we only need NER.
        """
        if not self.enabled:
            return
            
        try:
            self.nlp = spacy.load('en_core_web_sm', disable=['parser', 'lemmatizer'])
            logger.debug("spaCy NER model loaded")
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {e}")
            self.nlp = None
            
    def extract_entities(self, text: str) -> Set[str]:
        """Extract entities from text and filter against DevOps whitelist.
        
        Args:
            text: Text to extract entities from
        
        Returns:
            Set of DevOps entity names found in the text.
        
        Example:
            >>> ner.extract_entities('Kubernetes deployment on AWS')
            {'kubernetes', 'aws'}
        """
        if self.nlp is None or not self.enabled:
            return set()
            
        try:
            doc = self.nlp(text.lower())
            entities = set()
            
            for ent in doc.ents:
                if ent.text.lower() in self.devops_entities:
                    entities.add(ent.text.lower())
                    
            return entities
        except Exception as e:
            logger.warning(f"NER extraction failed: {e}")
            return set()
            
    def compute_ner_score(self, text: str) -> float:
        """Compute NER score based on DevOps entity matches.
        
        Args:
            text: Text to analyze
        
        Returns:
            Score based on number of DevOps entities (20 points per entity).
        
        Example:
            >>> ner.compute_ner_score('Kubernetes and Docker')
            40.0
        """
        if not self.enabled:
            return 0.0
            
        entities = self.extract_entities(text)
        if not entities:
            return 0.0
            
        return float(len(entities) * 20)
