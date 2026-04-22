import click
import sys
from tabulate import tabulate
from markdownify import markdownify as md
from devpulse.core.container import get_container
from devpulse.core.logging_config import setup_logging, get_logger
from devpulse.config import config as cfg_obj
import os

"""CLI module for DevPulse.

This module provides the command-line interface for DevPulse using Click.
Commands include:
- config: Show configuration paths
- fetch: Fetch articles from sources
- list: List articles
- search: Search articles
- save: Save an article
- saved: List saved articles
- train: Train NLP classifier
- analyze: Analyze article with NLP

Example:
    $ devpulse fetch kubernetes
    $ devpulse list --limit 10
    $ devpulse search docker
"""

logger = get_logger(__name__)

# Initialize logging on module load
setup_logging()


@click.group()
def main():
    """DevPulse CLI - DevOps content aggregator.
    
    Fetches, scores, and manages DevOps articles from multiple sources
    with optional NLP-based relevance analysis.
    """
    pass

@main.command()
@click.argument('topic', required=False)
def fetch(topic):
    """Fetch articles from sources.
    
    Fetches articles from configured sources and saves them to the database.
    Optionally filters by topic.
    
    Args:
        topic: Topic to filter by (optional)
    
    Example:
        $ devpulse fetch kubernetes
    """
    topic_str = f" for '{topic}'" if topic else ""
    click.echo(f"Fetching{topic_str}...")
    
    try:
        container = get_container()
        count = container.fetcher.fetch_all(topic)
        if count > 0:
            click.echo(f"Added {count} articles.")
        else:
            click.echo("No new articles found.")
    except Exception as e:
        logger.error(f"Fetch failed: {e}", exc_info=True)
        click.echo(f"Error: {e}")

@main.command()
@click.argument('query')
def search(query):
    """Search articles using full-text search.
    
    Uses SQLite FTS5 for efficient full-text search across
    article titles and content. Results are ranked by relevance.
    
    Args:
        query: Search query (supports boolean operators, phrases)
    
    Example:
        $ devpulse search kubernetes
        $ devpulse search "docker AND kubernetes"
    """
    try:
        container = get_container()
        articles = container.storage.search_articles(query)
        if not articles:
            click.echo("No results.")
            return

        table = []
        for art in articles:
            title = (art['title'][:60] + '..') if len(art['title']) > 60 else art['title']
            table.append([art['id'], art['score'], art['source'], title])
        
        click.echo(tabulate(table, headers=["ID", "Score", "Source", "Title"], tablefmt="simple"))
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        click.echo(f"Error: {e}")

@main.command()
@click.option('--limit', default=20, help='Number of articles to list')
@click.option('--offset', default=0, help='Offset for pagination')
def list(limit, offset):
    """List articles ordered by score and freshness.
    
    Displays articles in a table format with ID, score, source,
    and title. Articles are ordered by fetched_at DESC, score DESC.
    
    Args:
        limit: Maximum number of articles to display (default: 20)
        offset: Number of articles to skip for pagination (default: 0)
    
    Example:
        $ devpulse list --limit 10
        $ devpulse list --limit 5 --offset 10
    """
    try:
        container = get_container()
        articles = container.storage.list_articles(limit=limit, offset=offset)
        if not articles:
            click.echo("No articles found.")
            return

        table = []
        for art in articles:
            title = (art['title'][:60] + '..') if len(art['title']) > 60 else art['title']
            table.append([art['id'], art['score'], art['source'], title])
        
        click.echo(tabulate(table, headers=["ID", "Score", "Source", "Title"], tablefmt="simple"))
    except Exception as e:
        logger.error(f"List failed: {e}", exc_info=True)
        click.echo(f"Error: {e}")

@main.command()
@click.argument('id', type=int)
def read(id):
    """Read article.
    
    Displays article content, including title, source, score, and URL.
    
    Args:
        id: Article ID to read
    
    Example:
        $ devpulse read 123
    """
    try:
        container = get_container()
        art = container.storage.get_article(id)
        if not art:
            click.echo("Not found.")
            return

        click.echo(f"\n{art['title']}")
        click.echo(f"Source: {art['source']} | Score: {art['score']}")
        click.echo(f"URL: {art['url']}")
        click.echo("-" * 20)
        
        content = art['content'] or "No content."
        summary = content[:500] + "..." if len(content) > 500 else content
        click.echo(summary)
    except Exception as e:
        logger.error(f"Read failed: {e}", exc_info=True)
        click.echo(f"Error: {e}")

@main.command()
@click.argument('id', type=int)
def save(id):
    """Save an article to bookmarks.
    
    Marks an article as saved for later reference.
    Saved articles can be listed with the 'saved' command.
    
    Args:
        id: Article ID to save
    
    Example:
        $ devpulse save 123
    """
    try:
        container = get_container()
        art = container.storage.get_article(id)
        if not art:
            click.echo("Not found.")
            return

        container.storage.save_article(id)
        clean_title = "".join([c if c.isalnum() else "_" for c in art['title'][:50]])
        filename = f"{id}_{clean_title}.md"
        save_path = cfg_obj.save_dir / filename
        
        content_md = md(art['content'] or "")
        header = f"# {art['title']}\n\nSource: {art['source']}\nURL: {art['url']}\n\n---\n\n"
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(header + content_md)
        
        click.echo(f"Saved: {save_path}")
    except Exception as e:
        logger.error(f"Save failed: {e}", exc_info=True)
        click.echo(f"Error: {e}")

@main.command()
@click.confirmation_option(prompt='Are you sure you want to clear all articles? This cannot be undone.')
def clear():
    """Clear all articles from the database.
    
    This command removes all articles from the database and resets
    the full-text search index. Saved article bookmarks are preserved.
    
    Example:
        $ devpulse clear
    """
    try:
        container = get_container()
        container.storage.clear_articles()
        click.echo("All articles cleared from database.")
    except Exception as e:
        logger.error(f"Clear failed: {e}", exc_info=True)
        click.echo(f"Error: {e}")

@main.command()
def config():
    """Show configuration details.
    
    Displays configuration paths, including database and saved articles directory.
    
    Example:
        $ devpulse config
    """
    click.echo(f"Config path: {cfg_obj.config_path}")
    click.echo(f"Database path: {cfg_obj.db_path}")
    click.echo(f"Saved articles dir: {cfg_obj.save_dir}")
    click.echo("\nTo edit sources or weights, modify the config.yaml file.")

@main.command()
@click.option('--positive', help='Path to positive samples file')
@click.option('--negative', help='Path to negative samples file')
def train(positive, negative):
    """Train the NLP classifier.
    
    Trains a Naive Bayes classifier to distinguish between
    DevOps-relevant and non-DevOps content. Requires sample
    files with positive (DevOps) and negative (non-DevOps) examples.
    
    Args:
        positive: Path to file with DevOps-relevant samples
        negative: Path to file with non-DevOps samples
    
    Example:
        $ devpulse train --positive ~/.devpulse/corpus/sample_positive.txt \
        --negative ~/.devpulse/corpus/sample_negative.txt
    """
    if not positive or not negative:
        click.echo("Both --positive and --negative files are required.")
        return

    try:
        from devpulse.core.nlp.classifier import TextClassifier
        
        with open(positive, 'r', encoding='utf-8') as f:
            positive_samples = [line.strip() for line in f if line.strip()]
        with open(negative, 'r', encoding='utf-8') as f:
            negative_samples = [line.strip() for line in f if line.strip()]

        click.echo(f"Training with {len(positive_samples)} positive and {len(negative_samples)} negative samples...")
        classifier = TextClassifier()
        classifier.train(positive_samples, negative_samples)
        click.echo("Classifier trained successfully.")
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        click.echo(f"Training failed: {e}")

@main.command()
@click.argument('id', type=int)
def analyze(id):
    """Analyze an article with NLP breakdown.
    
    Shows detailed NLP analysis including:
    - Semantic score (TF-IDF + Cosine Similarity)
    - RAKE keyword extraction score
    - Classifier prediction (if trained)
    - Named Entity Recognition (NER) matches
    
    Args:
        id: Article ID to analyze
    
    Example:
        $ devpulse analyze 123
    """
    try:
        from devpulse.core.nlp.engine import NLPEngine
        from devpulse.core.nlp.classifier import TextClassifier
        from devpulse.core.nlp.ner import NEREngine
        
        container = get_container()
        art = container.storage.get_article(id)
        if not art:
            click.echo("Not found.")
            return

        text = f"{art['title']} {art['content']}"
        click.echo(f"\nAnalyzing: {art['title']}")
        click.echo("-" * 20)

        nlp_engine = NLPEngine()
        
        # Semantic Score (combined TF-IDF + Cosine Similarity)
        semantic_score = nlp_engine.compute_semantic_score(text)
        click.echo(f"Semantic Score: {semantic_score:.2f}")

        # RAKE Score
        rake_score = nlp_engine.compute_rake_score(text)
        click.echo(f"RAKE Score: {rake_score:.2f}")

        # Classifier
        classifier = TextClassifier()
        if classifier.is_model_trained():
            label, confidence = classifier.predict(text)
            click.echo(f"Classifier: {'Relevant' if label else 'Not Relevant'} ({confidence:.2f})")
        else:
            click.echo("Classifier: Not trained")

        # NER
        ner_engine = NEREngine()
        entities = ner_engine.extract_entities(text)
        click.echo(f"NER Entities: {', '.join(entities) if entities else 'None'}")
        click.echo(f"NER Score: {ner_engine.compute_ner_score(text):.2f}")
    except Exception as e:
        logger.error(f"Analyze failed: {e}", exc_info=True)
        click.echo(f"Error: {e}")

if __name__ == '__main__':
    main()
