from pathlib import Path
from typing import List, Set
import spacy
from devpulse.config import config


class NEREngine:
    def __init__(self):
        self.enabled = config.get('nlp.components.ner.enabled', True)
        self.model_path = Path.home() / '.devpulse' / config.get('nlp.model_path', 'models')
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # DevOps entity whitelist
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
        
        self.nlp = None
        self._load_model()
        
    def _load_model(self):
        """Load spaCy small model for efficiency."""
        if not self.enabled:
            return
            
        try:
            # Load small English model
            self.nlp = spacy.load('en_core_web_sm', disable=['parser', 'lemmatizer'])
        except Exception:
            # Model not installed, try to download or disable
            self.nlp = None
            
    def extract_entities(self, text: str) -> Set[str]:
        """Extract entities from text and filter against DevOps whitelist."""
        if self.nlp is None or not self.enabled:
            return set()
            
        try:
            doc = self.nlp(text.lower())
            entities = set()
            
            for ent in doc.ents:
                if ent.text.lower() in self.devops_entities:
                    entities.add(ent.text.lower())
                    
            return entities
        except Exception:
            return set()
            
    def compute_ner_score(self, text: str) -> float:
        """Compute NER score based on DevOps entity matches."""
        if not self.enabled:
            return 0.0
            
        entities = self.extract_entities(text)
        if not entities:
            return 0.0
            
        # Score based on number of matched entities
        return float(len(entities) * 20)  # 20 points per matched entity


ner_engine = NEREngine()
