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
        try:
            # Wipe previous data before each fetch to ensure freshness
            storage.clear_articles()
            
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
                    try:
                        count = future.result()
                        if count:
                            total_count += count
                    except Exception as e:
                        print(f"Worker thread error: {e}")

            return total_count
        except Exception as e:
            print(f"Error during collective fetch: {e}")
            return 0

    def _fetch_source(self, source, adapter, topic):
        try:
            raw_articles = adapter.fetch(source['url'])
            if not raw_articles:
                return 0
                
            count = 0
            for art in raw_articles:
                try:
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
                except Exception as art_err:
                    # Log error for specific article but continue with others
                    continue
            return count
        except Exception as e:
            # Silence specific source errors to keep CLI output clean, 
            # but return 0 to indicate no articles from this source
            return 0

fetcher = Fetcher()
