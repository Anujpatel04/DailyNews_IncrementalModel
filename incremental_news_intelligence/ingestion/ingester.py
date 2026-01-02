"""Article ingestion orchestrator."""
import logging
from typing import List, Optional

from incremental_news_intelligence.config.settings import HackerNewsConfig, NewsAPIAIConfig, SearchAPIConfig
from incremental_news_intelligence.ingestion.bing_client import SearchAPIClient
from incremental_news_intelligence.ingestion.hackernews_client import HackerNewsClient
from incremental_news_intelligence.ingestion.newsapi_ai_client import NewsAPIAIClient
from incremental_news_intelligence.storage.managers import RawArticleStorage

logger = logging.getLogger(__name__)

class ArticleIngester:
    """Orchestrates article ingestion from multiple data sources."""

    def __init__(
        self,
        search_api_config: SearchAPIConfig,
        raw_storage: RawArticleStorage,
        newsapi_ai_config: Optional[NewsAPIAIConfig] = None,
        hackernews_config: Optional[HackerNewsConfig] = None,
    ):
        """Initialize article ingester."""
        self.search_client = SearchAPIClient(search_api_config)
        self.storage = raw_storage
        self.search_config = search_api_config
        self.newsapi_ai_config = newsapi_ai_config
        self.newsapi_ai_client = None
        if newsapi_ai_config and newsapi_ai_config.enabled:
            self.newsapi_ai_client = NewsAPIAIClient(newsapi_ai_config)
        
        self.hackernews_config = hackernews_config
        self.hackernews_client = None
        if hackernews_config and hackernews_config.enabled:
            self.hackernews_client = HackerNewsClient(
                enabled=hackernews_config.enabled,
                rate_limit_per_minute=hackernews_config.rate_limit_per_minute
            )

    def _ingest_from_articles(self, articles: List[dict], source_name: str) -> int:
        """Helper to ingest articles from a list."""
        ingested_count = 0
        for article in articles:
            article_id = article.get("_article_id")
            if not article_id:
                logger.warning("Article missing ID, skipping")
                continue

            if self.storage.article_exists(article_id):
                logger.debug(f"Article {article_id} already exists, skipping")
                continue

            self.storage.save_article(article_id, article)
            ingested_count += 1

        return ingested_count

    def ingest_articles(
        self,
        query: str,
        max_articles: int = 50,
        freshness: str = "day",
    ) -> List[str]:
        """
        Ingest articles from all enabled data sources.

        Args:
            query: Search query
            max_articles: Maximum articles per source/engine
            freshness: Date filter (only for news engines)

        Returns:
            List of article IDs that were ingested
        """
        logger.info(f"Starting ingestion: query='{query}', max={max_articles} per source")

        all_ingested_ids = []
        
        for engine in self.search_config.enabled_engines:
            logger.info(f"Ingesting from SearchAPI {engine}...")
            
            use_freshness = freshness if engine in ["bing_news", "google_news"] else None
            
            articles = self.search_client.search_with_pagination(
                query=query,
                engine=engine,
                max_articles=max_articles,
                freshness=use_freshness,
            )

            engine_ingested = self._ingest_from_articles(articles, f"SearchAPI_{engine}")
            all_ingested_ids.extend([a.get("_article_id") for a in articles if a.get("_article_id")])
            logger.info(f"Ingested {engine_ingested} new articles from SearchAPI {engine}")

        if self.newsapi_ai_client:
            logger.info("Ingesting from NewsAPI.ai...")
            newsapi_engines = ["google_news"]
            
            for engine in newsapi_engines:
                logger.info(f"Ingesting from NewsAPI.ai {engine}...")
                
                articles = self.newsapi_ai_client.search_with_pagination(
                    query=query,
                    engine=engine,
                    max_articles=max_articles,
                    freshness=freshness,
                )

                engine_ingested = self._ingest_from_articles(articles, f"NewsAPI.ai_{engine}")
                all_ingested_ids.extend([a.get("_article_id") for a in articles if a.get("_article_id")])
                logger.info(f"Ingested {engine_ingested} new articles from NewsAPI.ai {engine}")

        if self.hackernews_client:
            logger.info("Ingesting from Hacker News...")
            
            for story_type in self.hackernews_config.fetch_types:
                logger.info(f"Fetching {story_type} from Hacker News...")
                
                articles = self.hackernews_client.fetch_stories(
                    story_type=story_type,
                    max_stories=self.hackernews_config.max_stories_per_type,
                )
                
                hn_ingested = self._ingest_from_articles(articles, f"HackerNews_{story_type}")
                all_ingested_ids.extend([a.get("_article_id") for a in articles if a.get("_article_id")])
                logger.info(f"Ingested {hn_ingested} new articles from Hacker News {story_type}")

        logger.info(f"Total ingested {len(all_ingested_ids)} new articles across all sources")
        return all_ingested_ids

