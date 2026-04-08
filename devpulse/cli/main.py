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

if __name__ == '__main__':
    main()
