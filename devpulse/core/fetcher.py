import concurrent.futures
from devpulse.core.adapters.rss import RSSAdapter, ScraperAdapter
from devpulse.core.scorer import scorer
from devpulse.core.storage import storage
from devpulse.config import config

class Fetcher:
    def __init__(self):
        self.rss_adapter = RSSAdapter()
        self.scraper_adapter = ScraperAdapter()

    def fetch_all(self, topic=None):
        sources = config.get('sources', {})
        total_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            # RSS Sources
            for src in sources.get('rss', []):
                futures.append(executor.submit(self._fetch_source, src, self.rss_adapter, topic))
            
            # Scraping Sources
            for src in sources.get('scraping', []):
                futures.append(executor.submit(self._fetch_source, src, self.scraper_adapter, topic))

            for future in concurrent.futures.as_completed(futures):
                count = future.result()
                if count:
                    total_count += count

        return total_count

    def _fetch_source(self, source, adapter, topic):
        try:
            raw_articles = adapter.fetch(source['url'])
            count = 0
            for art in raw_articles:
                score = scorer.calculate_score(art, topic)
                if scorer.is_relevant(score):
                    storage.add_article(
                        art['title'], 
                        art['url'], 
                        source['name'], 
                        score, 
                        art['content']
                    )
                    count += 1
            return count
        except Exception as e:
            # print(f"Error fetching {source['name']}: {e}")
            return 0

fetcher = Fetcher()
