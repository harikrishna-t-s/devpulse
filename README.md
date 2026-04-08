# DevPulse

High-quality DevOps content aggregator.

## Features

- **RSS/Scraping**: Fetches from 50+ DevOps sources.
- **Deterministic Scoring**: Keyword-based relevance ranking.
- **Local Storage**: SQLite database for metadata.
- **Offline Mode**: Save articles as Markdown.
- **FTS5 Search**: Fast full-text search.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Fetch latest content
devpulse fetch

# Fetch content for a specific topic
devpulse fetch kubernetes

# List articles
devpulse list --limit 10

# Read summary
devpulse read <id>

# Save article for offline reading
devpulse save <id>

# Show config
devpulse config
```

## Configuration

Modify `~/.devpulse/config.yaml` to add/remove sources or adjust keyword weights.
