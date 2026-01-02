"""Incremental embedding generation."""
import logging
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from incremental_news_intelligence.config.settings import EmbeddingConfig
from incremental_news_intelligence.storage.managers import (
    EmbeddingStorage,
    ProcessedArticleStorage,
)

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Generates embeddings for articles incrementally."""

    def __init__(
        self,
        config: EmbeddingConfig,
        processed_storage: ProcessedArticleStorage,
        embedding_storage: EmbeddingStorage,
    ):
        """Initialize embedding generator."""
        self.config = config
        self.processed_storage = processed_storage
        self.embedding_storage = embedding_storage
        self.model: Optional[SentenceTransformer] = None

    def _load_model(self) -> SentenceTransformer:
        """Lazy load embedding model."""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.config.model_name}")
            self.model = SentenceTransformer(
                self.config.model_name, device=self.config.device
            )
        return self.model

    def generate_embedding(self, article_id: str) -> Optional[List[float]]:
        """
        Generate embedding for single article if not already exists.

        Args:
            article_id: Article ID

        Returns:
            Embedding vector or None if article not found
        """
        if self.embedding_storage.has_embedding(article_id):
            logger.debug(f"Embedding for {article_id} already exists")
            return self.embedding_storage.get_embedding(article_id)

        processed_article = self.processed_storage.load_processed_article(article_id)
        if not processed_article:
            logger.warning(f"Processed article {article_id} not found")
            return None

        text = processed_article.get("text", "")
        if not text:
            logger.warning(f"Article {article_id} has no text")
            return None

        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        embedding_list = embedding.tolist()

        metadata = {
            "article_id": article_id,
            "model_name": self.config.model_name,
            "text_length": len(text),
        }

        self.embedding_storage.save_embedding(article_id, embedding_list, metadata)
        logger.debug(f"Generated embedding for {article_id}")
        return embedding_list

    def generate_embeddings_batch(self, article_ids: List[str]) -> List[str]:
        """
        Generate embeddings for multiple articles.

        Args:
            article_ids: List of article IDs

        Returns:
            List of article IDs with successfully generated embeddings
        """
        model = self._load_model()
        processed_ids = []

        for article_id in article_ids:
            if self.embedding_storage.has_embedding(article_id):
                continue

            processed_article = self.processed_storage.load_processed_article(
                article_id
            )
            if not processed_article:
                continue

            text = processed_article.get("text", "")
            if not text:
                continue

            embedding = model.encode(text, convert_to_numpy=True)
            embedding_list = embedding.tolist()

            metadata = {
                "article_id": article_id,
                "model_name": self.config.model_name,
                "text_length": len(text),
            }

            self.embedding_storage.save_embedding(
                article_id, embedding_list, metadata
            )
            processed_ids.append(article_id)

        logger.info(f"Generated embeddings for {len(processed_ids)} articles")
        return processed_ids

    def generate_new_embeddings(self) -> List[str]:
        """
        Generate embeddings for all articles without embeddings.

        Returns:
            List of article IDs with newly generated embeddings
        """
        processed_ids = self.processed_storage.list_article_ids()
        embedding_ids = set(self.embedding_storage.list_article_ids())

        new_ids = [aid for aid in processed_ids if aid not in embedding_ids]

        if not new_ids:
            logger.info("No new articles to embed")
            return []

        return self.generate_embeddings_batch(new_ids)


