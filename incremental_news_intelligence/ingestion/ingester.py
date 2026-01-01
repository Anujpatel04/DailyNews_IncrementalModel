"""Article ingestion orchestrator."""
import logging
from typing import List

from incremental_news_intelligence.config.settings import BingNewsConfig
from incremental_news_intelligence.ingestion.bing_client import BingNewsClient
from incremental_news_intelligence.storage.managers import RawArticleStorage

logger = logging.getLogger(__name__)

class ArticleIngester:
    """Orchestrates article ingestion from Bing News API."""

    def __init__(
        self,
        bing_config: BingNewsConfig,
        raw_storage: RawArticleStorage,
    ):
        """Initialize article ingester."""
        self.client = BingNewsClient(bing_config)
        self.storage = raw_storage

    def ingest_articles(
        self,
        query: str,
        max_articles: int = 50,
        freshness: str = "day",
    ) -> List[str]:
        """
        Ingest articles from Bing News API.

        Args:
            query: Search query
            max_articles: Maximum articles to ingest
            freshness: Date filter

        Returns:
            List of article IDs that were ingested
        """
        logger.info(f"Starting ingestion: query='{query}', max={max_articles}")

        articles = self.client.search_with_pagination(
            query=query,
            max_articles=max_articles,
            freshness=freshness,
        )

        ingested_ids = []
        for article in articles:
            article_id = article.get("_article_id")
            if not article_id:
                logger.warning("Article missing ID, skipping")
                continue

            if self.storage.article_exists(article_id):
                logger.debug(f"Article {article_id} already exists, skipping")
                continue

            self.storage.save_article(article_id, article)
            ingested_ids.append(article_id)

        logger.info(f"Ingested {len(ingested_ids)} new articles")
        return ingested_ids
