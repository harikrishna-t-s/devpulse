# Developer Guide

This guide provides detailed information for contributors to DevPulse.

## Architecture Overview

DevPulse follows clean architecture principles with clear separation of concerns:

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                           │
│                      (cli/main.py)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Dependency Injection                       │
│                  (core/container.py)                         │
└──────┬──────────────┬──────────────┬─────────────────────────┘
       │              │              │
┌──────▼──────┐ ┌────▼──────┐ ┌───▼────────┐
│  Storage    │ │  Scorer   │ │  Fetcher   │
│(storage.py) │ │(scorer.py)│ │(fetcher.py)│
└─────────────┘ └───────────┘ └────────────┘
       │              │              │
       └──────────────┴──────────────┘
                      │
         ┌────────────▼────────────┐
         │   Topic Filter          │
         │ (topic_filter.py)       │
         └─────────────────────────┘
                      │
         ┌────────────▼────────────┐
         │   NLP Components        │
         │ (nlp/engine.py)         │
         │ (nlp/classifier.py)     │
         │ (nlp/ner.py)            │
         └─────────────────────────┘
```

### Key Design Patterns

1. **Dependency Injection**: Components are created and injected via `Container` class
2. **Protocol-Based Design**: Interfaces defined using Python's `Protocol` for flexibility
3. **Lazy Loading**: Heavy components (NLP) loaded on-demand
4. **Separation of Concerns**: Each module has a single responsibility
5. **Configuration-Driven**: Behavior controlled via YAML configuration

## Module Documentation

### Core Modules

#### `core/container.py`
- **Purpose**: Dependency injection container
- **Key Classes**: `Container`, `StorageProtocol`, `ScorerProtocol`, `FetcherProtocol`
- **Usage**: Use `get_container()` to access component instances

#### `core/storage.py`
- **Purpose**: SQLite storage with FTS5 full-text search
- **Key Classes**: `SQLiteStorage`
- **Schema**: `articles`, `saved`, `articles_fts` (virtual table)
- **Triggers**: Automatic FTS index synchronization

#### `core/scorer.py`
- **Purpose**: Article relevance scoring
- **Key Classes**: `ArticleScorer`
- **Scoring Pipeline**: Topic filter → Topic weighting → Keyword scoring → Freshness boost → NLP scoring

#### `core/fetcher.py`
- **Purpose**: Content aggregation from multiple sources
- **Key Classes**: `ArticleFetcher`
- **Concurrency**: ThreadPoolExecutor with max_workers=10

#### `core/topic_filter.py`
- **Purpose**: Topic-based article validation
- **Key Classes**: `TopicFilter`
- **SRP Compliance**: Separates filtering logic from scoring

### NLP Modules

#### `core/nlp/engine.py`
- **Purpose**: Semantic analysis using TF-IDF, cosine similarity, and RAKE
- **Key Classes**: `NLPEngine`
- **Lazy Initialization**: Components loaded on first use
- **Combined Scoring**: TF-IDF and cosine similarity merged into semantic score

#### `core/nlp/classifier.py`
- **Purpose**: Naive Bayes text classifier
- **Key Classes**: `TextClassifier`
- **Persistence**: Models saved via joblib
- **Training**: Requires positive and negative samples

#### `core/nlp/ner.py`
- **Purpose**: Named Entity Recognition for DevOps entities
- **Key Classes**: `NEREngine`
- **Whitelist**: Predefined DevOps entity names
- **Model**: spaCy en_core_web_sm (parser/lemmatizer disabled)

### Adapters

#### `core/adapters/rss.py`
- **Purpose**: Content source adapters
- **Key Classes**: `BaseAdapter`, `RSSAdapter`, `ScraperAdapter`
- **Extensibility**: Implement `BaseAdapter` for new sources

### Utilities

#### `utils/networking.py`
- **Purpose**: HTTP utilities with connection pooling
- **Key Functions**: `get_session()`, `fetch_url()`, `sanitize_text()`
- **Optimization**: Reusable session for connection reuse

## Development Workflow

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/devpulse.git
cd devpulse

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .[dev]

# Install spaCy model for NER
python -m spacy download en_core_web_sm
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=devpulse --cov-report=html

# Run specific test file
pytest tests/test_storage.py

# Run with verbose output
pytest -v
```

### Code Style Guidelines

DevPulse follows these conventions:

1. **Type Hints**: All public APIs must have type hints
2. **Docstrings**: Google-style docstrings for all classes and public methods
3. **Logging**: Use `get_logger(__name__)` for module-level loggers
4. **Error Handling**: Log exceptions with `exc_info=True` for debugging
5. **Configuration**: Use `config.get(key, default)` for config access

### Adding New Features

#### Adding a New Content Source

1. Add source to `config.yaml`:
```yaml
sources:
  rss:
    - name: New Source
      url: https://example.com/feed.xml
```

2. For scraping, add adapter logic in `adapters/rss.py`:
```python
class NewScraperAdapter(BaseAdapter):
    def fetch(self, url: str) -> List[Dict[str, Any]]:
        # Implement scraping logic
        pass
```

3. Register in `fetcher.py`:
```python
for src in sources.get('new_source', []):
    futures.append(executor.submit(self._fetch_source, src, new_adapter, topic))
```

#### Adding a New NLP Component

1. Create new module in `core/nlp/`:
```python
class NewNLPComponent:
    def __init__(self) -> None:
        self.enabled = config.get('nlp.components.new.enabled', True)
    
    def compute_score(self, text: str) -> float:
        # Implement scoring logic
        pass
```

2. Integrate in `scorer.py`:
```python
def _get_new_component(self) -> Optional[Any]:
    if self._new_component is None and self.nlp_enabled:
        from devpulse.core.nlp.new_component import NewNLPComponent
        self._new_component = NewNLPComponent()
    return self._new_component
```

3. Add to scoring pipeline in `_add_nlp_scores()`

## Testing Guidelines

### Unit Tests

Test individual components in isolation:

```python
def test_topic_filter():
    filter = TopicFilter()
    article = {'title': 'Kubernetes guide', 'content': 'Learn k8s'}
    assert filter.is_valid(article, topic='kubernetes') is True
    assert filter.is_valid(article, topic='docker') is False
```

### Integration Tests

Test component interactions:

```python
def test_fetch_and_score():
    container = create_container()
    count = container.fetcher.fetch_all(topic='kubernetes')
    assert count > 0
```

### Mocking Dependencies

Use dependency injection for testability:

```python
def test_scorer_with_mock_filter():
    mock_filter = Mock()
    mock_filter.is_valid.return_value = True
    scorer = ArticleScorer(topic_filter=mock_filter)
    score = scorer.calculate_score(article, topic='kubernetes')
    assert score > 0
```

## Performance Considerations

### Database Optimization

- Use FTS5 for full-text search (already implemented)
- Add indexes on frequently queried columns if needed
- Consider connection pooling for high-concurrency scenarios

### NLP Performance

- NLP components are lazy-loaded to improve startup time
- Consider caching NLP results for frequently accessed articles
- Disable NLP components if not needed for your use case

### Network Optimization

- HTTP session pooling is already implemented
- Consider increasing timeout for slow sources
- Implement retry logic for transient failures

## Debugging

### Enabling Debug Logging

```bash
export DEVPULSE_LOG_LEVEL=DEBUG
devpulse fetch
```

### Common Issues

**NLP components not loading:**
- Check spaCy model: `python -m spacy download en_core_web_sm`
- Verify NLTK resources (auto-downloaded on first use)
- Check NLP is enabled in config.yaml

**Database locked:**
- Ensure only one DevPulse instance is running
- Check for orphaned connections
- Reset database: `rm ~/.devpulse/devpulse.db`

**Memory issues with large fetches:**
- Reduce ThreadPoolExecutor max_workers
- Process articles in batches
- Consider pagination for list operations

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Tag release: `git tag -a v1.0.0 -m "Release version 1.0.0"`
5. Push tag: `git push origin v1.0.0`
6. Build and publish to PyPI (if applicable)

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes following code style guidelines
4. Add tests for new functionality
5. Ensure all tests pass
6. Update documentation as needed
7. Submit pull request with descriptive message

### Code Review Checklist

- [ ] Type hints on all public APIs
- [ ] Google-style docstrings
- [ ] Error handling with logging
- [ ] No global singletons (use DI)
- [ ] Tests added for new features
- [ ] Documentation updated
- [ ] No breaking changes (or documented)

## License

MIT License - see LICENSE file for details.
