# DevPulse

A production-grade DevOps content aggregator with intelligent scoring and NLP-based relevance analysis.

## Features

- **Multi-Source Aggregation**: Fetches from RSS feeds and web scraping (50+ DevOps sources)
- **Intelligent Scoring**: Keyword-based relevance ranking with configurable weights
- **NLP Analysis**: Optional semantic analysis using TF-IDF, cosine similarity, RAKE, and NER
- **Machine Learning**: Trainable Naive Bayes classifier for content relevance
- **Local Storage**: SQLite database with FTS5 full-text search
- **Offline Mode**: Save articles as Markdown for offline reading
- **Dependency Injection**: Clean architecture with testable components
- **Structured Logging**: Comprehensive logging for debugging and monitoring

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/devpulse.git
cd devpulse

# Install in development mode
pip install -e .

# Optional: Install spaCy model for NER
python -m spacy download en_core_web_sm
```

## Quick Start

```bash
# Fetch latest DevOps content
devpulse fetch

# Fetch content for a specific topic
devpulse fetch kubernetes

# List articles (ordered by score and freshness)
devpulse list --limit 10

# Search articles using full-text search
devpulse search "docker AND kubernetes"

# Read an article summary
devpulse read <id>

# Save article as Markdown for offline reading
devpulse save <id>

# Analyze article with NLP breakdown
devpulse analyze <id>

# Show configuration paths
devpulse config
```

## NLP Features

DevPulse includes optional NLP capabilities for enhanced relevance scoring:

### Training the Classifier

```bash
# Train the Naive Bayes classifier with sample data
devpulse train --positive ~/.devpulse/corpus/sample_positive.txt \
                --negative ~/.devpulse/corpus/sample_negative.txt
```

### NLP Analysis

```bash
# View detailed NLP breakdown for an article
devpulse analyze <id>
```

Output includes:
- **Semantic Score**: Combined TF-IDF and cosine similarity (0-100)
- **RAKE Score**: Keyword extraction score (0-100)
- **Classifier**: ML prediction with confidence (if trained)
- **NER Entities**: DevOps entities detected (e.g., kubernetes, docker, aws)

## Configuration

Configuration is managed via `~/.devpulse/config.yaml`. Key sections:

### Sources

```yaml
sources:
  rss:
    - name: Kubernetes Blog
      url: https://kubernetes.io/feed/
  scraping:
    - name: GitHub Trending
      url: https://github.com/trending
```

### Scoring

```yaml
scoring:
  threshold: 50          # Minimum score for relevance
  weights:
    kubernetes: 100
    docker: 80
    aws: 70
  freshness_boost: 20    # Bonus for recent articles
```

### NLP Configuration

```yaml
nlp:
  enabled: true
  model_path: models
  corpus_path: corpus
  components:
    tfidf:
      enabled: true
      weight: 0.3
    cosine_similarity:
      enabled: true
      weight: 0.2
    rake:
      enabled: true
      weight: 0.15
    classifier:
      enabled: true
      weight: 0.2
    ner:
      enabled: true
      weight: 0.15
```

## Architecture

DevPulse follows clean architecture principles:

- **Dependency Injection**: Components managed via `Container` class
- **Separation of Concerns**: Topic filtering, scoring, and storage are separate modules
- **Lazy Loading**: NLP components loaded on-demand for faster startup
- **Type Hints**: Full type annotations for better IDE support and static analysis
- **Structured Logging**: Centralized logging configuration with configurable levels

### Module Structure

```
devpulse/
├── core/
│   ├── container.py      # Dependency injection
│   ├── storage.py        # SQLite storage with FTS5
│   ├── scorer.py         # Article scoring logic
│   ├── fetcher.py        # Content aggregation
│   ├── topic_filter.py   # Topic validation
│   ├── logging_config.py # Logging setup
│   ├── models.py         # Pydantic data models
│   ├── adapters/
│   │   └── rss.py        # RSS and scraping adapters
│   └── nlp/
│       ├── engine.py     # Semantic analysis
│       ├── classifier.py # ML classifier
│       └── ner.py        # Named Entity Recognition
├── cli/
│   └── main.py           # CLI commands
├── utils/
│   └── networking.py    # HTTP utilities
└── config.py             # Configuration management
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install pytest pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=devpulse
```

### Code Style

DevPulse follows PEP 8 and uses:
- Type hints for all public APIs
- Google-style docstrings
- Structured logging
- Dependency injection for testability

### Adding New Sources

1. Add source to `config.yaml` under `sources.rss` or `sources.scraping`
2. For scraping, create a new adapter method in `adapters/rss.py`
3. Test with `devpulse fetch`

## Troubleshooting

### NLP Components Not Loading

If NLP features fail to load:
- Ensure spaCy model is installed: `python -m spacy download en_core_web_sm`
- Check NLTK resources are downloaded (automatic on first use)
- Verify NLP is enabled in config.yaml

### Database Issues

```bash
# Reset database (WARNING: deletes all articles)
rm ~/.devpulse/devpulse.db
```

### Logging

Enable debug logging:

```bash
# Set log level in config.yaml or environment
export DEVPULSE_LOG_LEVEL=DEBUG
devpulse fetch
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please see DEVELOPER.md for contribution guidelines.
