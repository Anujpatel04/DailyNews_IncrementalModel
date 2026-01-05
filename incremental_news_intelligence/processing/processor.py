"""Processing layer orchestrator."""
import logging
from typing import List, Optional

from incremental_news_intelligence.processing.normalizer import ArticleProcessor
from incremental_news_intelligence.storage.managers import (
    ProcessedArticleStorage,
    RawArticleStorage,
)

logger = logging.getLogger(__name__)

class ProcessingOrchestrator:
    """Orchestrates article processing pipeline."""

    def __init__(
        self,
        raw_storage: RawArticleStorage,
        processed_storage: ProcessedArticleStorage,
        similarity_threshold: float = 0.9,
    ):
        """Initialize processing orchestrator."""
        self.raw_storage = raw_storage
        self.processed_storage = processed_storage
        self.processor = ArticleProcessor(similarity_threshold=similarity_threshold)

    def process_article(self, article_id: str) -> Optional[str]:
        """
        Process single article.

        Args:
            article_id: Article ID to process

        Returns:
            Article ID if successfully processed, None otherwise
        """
        if self.processed_storage.processed_article_exists(article_id):
            logger.debug(f"Article {article_id} already processed")
            return article_id

        raw_article = self.raw_storage.load_article(article_id)
        if not raw_article:
            logger.warning(f"Raw article {article_id} not found")
            return None

        processed = self.processor.process_article(raw_article)
        if not processed:
            logger.debug(f"Article {article_id} filtered during processing")
            return None

        self.processed_storage.save_processed_article(article_id, processed)
        logger.debug(f"Processed article {article_id}")
        return article_id

    def process_new_articles(self) -> List[str]:
        """
        Process all unprocessed articles.

        Returns:
            List of processed article IDs
        """
        raw_ids = self.raw_storage.list_article_ids()
        processed_ids = []

        for article_id in raw_ids:
            result = self.process_article(article_id)
            if result:
                processed_ids.append(result)

        logger.info(f"Processed {len(processed_ids)} articles")
        return processed_ids






