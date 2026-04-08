import feedparser
from devpulse.utils.networking import fetch_url
from bs4 import BeautifulSoup

class BaseAdapter:
    def fetch(self, url):
        raise NotImplementedError

class RSSAdapter(BaseAdapter):
    def fetch(self, url):
        # feedparser handles the request usually, but let's use our session for consistency if possible
        # or just use feedparser's built-in support
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries:
            articles.append({
                'title': entry.get('title', ''),
                'url': entry.get('link', ''),
                'content': entry.get('summary', '') or entry.get('description', ''),
                'published': entry.get('published', '')
            })
        return articles

class ScraperAdapter(BaseAdapter):
    def fetch(self, url):
        html = fetch_url(url)
        if not html:
            return []
        
        articles = []
        soup = BeautifulSoup(html, 'html.parser')
        
        if "github.com/trending" in url:
            for repo in soup.select('article.Box-row'):
                title = repo.select_one('h2 a').text.strip().replace('\n', '').replace(' ', '')
                link = "https://github.com" + repo.select_one('h2 a')['href']
                desc = repo.select_one('p').text.strip() if repo.select_one('p') else ""
                articles.append({
                    'title': title,
                    'url': link,
                    'content': desc,
                    'published': None
                })
        elif "github.com/topics/devops" in url:
            for repo in soup.select('article.border'):
                title_elem = repo.select_one('h3 a.text-bold')
                if not title_elem: continue
                link = "https://github.com" + title_elem['href']
                title = title_elem.text.strip()
                desc = repo.select_one('div.color-fg-muted').text.strip() if repo.select_one('div.color-fg-muted') else ""
                articles.append({
                    'title': title,
                    'url': link,
                    'content': desc,
                    'published': None
                })
        
        return articles
