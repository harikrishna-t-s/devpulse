import click
import sys
from tabulate import tabulate
from markdownify import markdownify as md
from devpulse.core.fetcher import fetcher
from devpulse.core.storage import storage
from devpulse.config import config as cfg_obj
from devpulse.core.nlp.engine import nlp_engine
from devpulse.core.nlp.classifier import classifier
from devpulse.core.nlp.ner import ner_engine
import os

@click.group()
def main():
    """DevPulse: DevOps Content Aggregator"""
    pass

def echo_success(msg):
    click.secho(f"✔ {msg}", fg="green", bold=True)

def echo_info(msg):
    click.secho(f"ℹ {msg}", fg="blue")

def echo_warning(msg):
    click.secho(f"⚠ {msg}", fg="yellow")

def echo_error(msg):
    click.secho(f"✘ {msg}", fg="red", err=True)

@main.command()
@click.argument('topic', required=False)
def fetch(topic):
    """Fetch latest content"""
    topic_str = f" for '{topic}'" if topic else ""
    click.echo(f"Fetching{topic_str}...")
    
    try:
        count = fetcher.fetch_all(topic)
        if count > 0:
            click.echo(f"Added {count} articles.")
        else:
            click.echo("No new articles found.")
    except Exception as e:
        click.echo(f"Error: {e}")

@main.command()
@click.argument('query')
def search(query):
    """Search articles"""
    try:
        articles = storage.search_articles(query)
        if not articles:
            click.echo("No results.")
            return

        table = []
        for art in articles:
            title = (art['title'][:60] + '..') if len(art['title']) > 60 else art['title']
            table.append([art['id'], art['score'], art['source'], title])
        
        click.echo(tabulate(table, headers=["ID", "Score", "Source", "Title"], tablefmt="simple"))
    except Exception as e:
        click.echo(f"Error: {e}")

@main.command()
@click.option('--limit', default=20, help='Limit')
def list(limit):
    """List articles"""
    try:
        articles = storage.list_articles(limit=limit)
        if not articles:
            click.echo("No articles found.")
            return

        table = []
        for art in articles:
            title = (art['title'][:60] + '..') if len(art['title']) > 60 else art['title']
            table.append([art['id'], art['score'], art['source'], title])
        
        click.echo(tabulate(table, headers=["ID", "Score", "Source", "Title"], tablefmt="simple"))
    except Exception as e:
        click.echo(f"Error: {e}")

@main.command()
@click.argument('id', type=int)
def read(id):
    """Read article"""
    try:
        art = storage.get_article(id)
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
        click.echo(f"Error: {e}")

@main.command()
@click.argument('id', type=int)
def save(id):
    """Save article"""
    try:
        art = storage.get_article(id)
        if not art:
            click.echo("Not found.")
            return

        storage.save_article(id)
        clean_title = "".join([c if c.isalnum() else "_" for c in art['title'][:50]])
        filename = f"{id}_{clean_title}.md"
        save_path = cfg_obj.save_dir / filename
        
        content_md = md(art['content'] or "")
        header = f"# {art['title']}\n\nSource: {art['source']}\nURL: {art['url']}\n\n---\n\n"
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(header + content_md)
        
        click.echo(f"Saved: {save_path}")
    except Exception as e:
        click.echo(f"Error: {e}")

@main.command()
def config():
    """Show configuration details"""
    click.echo(f"Config path: {cfg_obj.config_path}")
    click.echo(f"Database path: {cfg_obj.db_path}")
    click.echo(f"Saved articles dir: {cfg_obj.save_dir}")
    click.echo("\nTo edit sources or weights, modify the config.yaml file.")

@main.command()
@click.option('--positive', help='File with positive samples (DevOps articles)')
@click.option('--negative', help='File with negative samples (non-DevOps articles)')
def train(positive, negative):
    """Train the Naive Bayes classifier"""
    if not positive or not negative:
        click.echo("Both --positive and --negative files are required.")
        return

    try:
        with open(positive, 'r', encoding='utf-8') as f:
            positive_samples = [line.strip() for line in f if line.strip()]
        with open(negative, 'r', encoding='utf-8') as f:
            negative_samples = [line.strip() for line in f if line.strip()]

        click.echo(f"Training with {len(positive_samples)} positive and {len(negative_samples)} negative samples...")
        classifier.train(positive_samples, negative_samples)
        click.echo("Classifier trained successfully.")
    except Exception as e:
        click.echo(f"Training failed: {e}")

@main.command()
@click.argument('id', type=int)
def analyze(id):
    """Analyze an article with NLP breakdown"""
    art = storage.get_article(id)
    if not art:
        click.echo("Not found.")
        return

    text = f"{art['title']} {art['content']}"
    click.echo(f"\nAnalyzing: {art['title']}")
    click.echo("-" * 20)

    # TF-IDF Score
    tfidf_score = nlp_engine.compute_tfidf_score(text)
    click.echo(f"TF-IDF Score: {tfidf_score:.2f}")

    # Cosine Similarity Score
    cos_score = nlp_engine.compute_cosine_similarity_score(text)
    click.echo(f"Cosine Similarity Score: {cos_score:.2f}")

    # RAKE Score
    rake_score = nlp_engine.compute_rake_score(text)
    click.echo(f"RAKE Score: {rake_score:.2f}")

    # Classifier
    if classifier.is_model_trained():
        label, confidence = classifier.predict(text)
        click.echo(f"Classifier: {'Relevant' if label else 'Not Relevant'} ({confidence:.2f})")
    else:
        click.echo("Classifier: Not trained")

    # NER
    entities = ner_engine.extract_entities(text)
    click.echo(f"NER Entities: {', '.join(entities) if entities else 'None'}")
    click.echo(f"NER Score: {ner_engine.compute_ner_score(text):.2f}")

if __name__ == '__main__':
    main()
