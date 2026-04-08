import click
import sys
from tabulate import tabulate
from markdownify import markdownify as md
from devpulse.core.fetcher import fetcher
from devpulse.core.storage import storage
from devpulse.config import config as cfg_obj
import os

@click.group()
def main():
    """DevPulse: DevOps Content Aggregator"""
    pass

@main.command()
@click.argument('topic', required=False)
def fetch(topic):
    """Retrieve latest articles (optionally filtered by topic)"""
    click.echo(f"Fetching latest DevOps content{' for ' + topic if topic else ''}...")
    count = fetcher.fetch_all(topic)
    click.echo(f"Added {count} relevant articles to the database.")

@main.command()
@click.option('--limit', default=20, help='Number of articles to list')
def list(limit):
    """Display curated articles"""
    articles = storage.list_articles(limit=limit)
    if not articles:
        click.echo("No articles found. Try running 'devpulse fetch' first.")
        return

    table = []
    for art in articles:
        table.append([art['id'], art['score'], art['source'], art['title'][:60]])
    
    click.echo(tabulate(table, headers=["ID", "Score", "Source", "Title"]))

@main.command()
@click.argument('id', type=int)
def read(id):
    """Print article summary and URL"""
    art = storage.get_article(id)
    if not art:
        click.echo(f"Article with ID {id} not found.")
        return

    click.echo(f"\nTitle: {art['title']}")
    click.echo(f"Source: {art['source']} | Score: {art['score']}")
    click.echo(f"URL: {art['url']}")
    click.echo("-" * 40)
    # Simple summary: first 500 chars
    summary = art['content'][:500] + "..." if len(art['content']) > 500 else art['content']
    click.echo(summary)
    click.echo("-" * 40)

@main.command()
@click.argument('id', type=int)
def save(id):
    """Extract and save full article content to a local file"""
    art = storage.get_article(id)
    if not art:
        click.echo(f"Article with ID {id} not found.")
        return

    storage.save_article(id)
    
    # Save as markdown
    filename = f"{id}_{art['title'][:50].replace(' ', '_').replace('/', '_')}.md"
    save_path = cfg_obj.save_dir / filename
    
    content_md = md(art['content'])
    header = f"# {art['title']}\n\nSource: {art['source']}\nURL: {art['url']}\n\n"
    
    with open(save_path, 'w') as f:
        f.write(header + content_md)
    
    click.echo(f"Article saved to {save_path}")

@main.command()
def config():
    """Show configuration details"""
    click.echo(f"Config path: {cfg_obj.config_path}")
    click.echo(f"Database path: {cfg_obj.db_path}")
    click.echo(f"Saved articles dir: {cfg_obj.save_dir}")
    click.echo("\nTo edit sources or weights, modify the config.yaml file.")

if __name__ == '__main__':
    main()
