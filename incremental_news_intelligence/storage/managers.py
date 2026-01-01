"""Storage managers for different data types."""
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from incremental_news_intelligence.config.settings import StorageConfig
from incremental_news_intelligence.storage.base import FileStorageBackend, VectorStorageBackend

logger = logging.getLogger(__name__)


class RawArticleStorage:
    """Storage manager for raw articles from Bing News API."""

    def __init__(self, storage_config: StorageConfig):
        """Initialize raw article storage."""
        self.backend = FileStorageBackend(storage_config.raw_articles_dir)

    def save_article(self, article_id: str, article_data: Dict[str, Any]) -> None:
        """Save raw article with ingestion timestamp."""
        article_data["_ingestion_timestamp"] = datetime.utcnow().isoformat()
        self.backend.save(article_id, article_data)

    def load_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Load raw article."""
        return self.backend.load(article_id)

    def article_exists(self, article_id: str) -> bool:
        """Check if article exists."""
        return self.backend.exists(article_id)

    def list_article_ids(self) -> List[str]:
        """List all article IDs."""
        return self.backend.list_keys()


class ProcessedArticleStorage:
    """Storage manager for processed articles."""

    def __init__(self, storage_config: StorageConfig):
        """Initialize processed article storage."""
        self.backend = FileStorageBackend(storage_config.processed_articles_dir)

    def save_processed_article(
        self, article_id: str, processed_data: Dict[str, Any]
    ) -> None:
        """Save processed article."""
        processed_data["_processing_timestamp"] = datetime.utcnow().isoformat()
        self.backend.save(article_id, processed_data)

    def load_processed_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Load processed article."""
        return self.backend.load(article_id)

    def processed_article_exists(self, article_id: str) -> bool:
        """Check if processed article exists."""
        return self.backend.exists(article_id)

    def list_article_ids(self) -> List[str]:
        """List all processed article IDs."""
        return self.backend.list_keys()


class EmbeddingStorage:
    """Storage manager for embeddings."""

    def __init__(self, storage_config: StorageConfig):
        """Initialize embedding storage."""
        self.backend = VectorStorageBackend(storage_config.embeddings_dir)

    def save_embedding(
        self,
        article_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """Save embedding with metadata."""
        self.backend.add_embedding(article_id, embedding, metadata)

    def get_embedding(self, article_id: str) -> Optional[List[float]]:
        """Get embedding for article."""
        return self.backend.get_embedding(article_id)

    def has_embedding(self, article_id: str) -> bool:
        """Check if embedding exists."""
        return self.backend.has_embedding(article_id)

    def get_all_embeddings(self) -> Dict[str, List[float]]:
        """Get all embeddings."""
        return self.backend.get_all_embeddings()

    def get_metadata(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for article."""
        return self.backend.get_metadata(article_id)

    def list_article_ids(self) -> List[str]:
        """List all article IDs with embeddings."""
        return self.backend.list_article_ids()


class ClusterStorage:
    """Storage manager for cluster state."""

    def __init__(self, storage_config: StorageConfig):
        """Initialize cluster storage."""
        self.backend = FileStorageBackend(storage_config.clusters_dir)

    def save_cluster(self, cluster_id: str, cluster_data: Dict[str, Any]) -> None:
        """Save cluster state."""
        cluster_data["_last_updated"] = datetime.utcnow().isoformat()
        self.backend.save(cluster_id, cluster_data)

    def load_cluster(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Load cluster state."""
        return self.backend.load(cluster_id)

    def cluster_exists(self, cluster_id: str) -> bool:
        """Check if cluster exists."""
        return self.backend.exists(cluster_id)

    def list_cluster_ids(self) -> List[str]:
        """List all cluster IDs."""
        return self.backend.list_keys()

    def get_all_clusters(self) -> Dict[str, Dict[str, Any]]:
        """Get all clusters."""
        clusters = {}
        for cluster_id in self.list_cluster_ids():
            cluster = self.load_cluster(cluster_id)
            if cluster:
                clusters[cluster_id] = cluster
        return clusters


class TopicStorage:
    """Storage manager for topic statistics."""

    def __init__(self, storage_config: StorageConfig):
        """Initialize topic storage."""
        self.backend = FileStorageBackend(storage_config.topics_dir)

    def save_topic_stats(
        self, cluster_id: str, topic_stats: Dict[str, Any]
    ) -> None:
        """Save topic statistics for cluster."""
        topic_stats["_last_updated"] = datetime.utcnow().isoformat()
        self.backend.save(cluster_id, topic_stats)

    def load_topic_stats(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Load topic statistics for cluster."""
        return self.backend.load(cluster_id)

    def topic_stats_exist(self, cluster_id: str) -> bool:
        """Check if topic stats exist."""
        return self.backend.exists(cluster_id)


class TrendStorage:
    """Storage manager for trend metrics."""

    def __init__(self, storage_config: StorageConfig):
        """Initialize trend storage."""
        self.backend = FileStorageBackend(storage_config.trends_dir)

    def save_trend_metrics(
        self, timestamp: str, trend_data: Dict[str, Any]
    ) -> None:
        """Save trend metrics for timestamp."""
        self.backend.save(timestamp, trend_data)

    def load_trend_metrics(self, timestamp: str) -> Optional[Dict[str, Any]]:
        """Load trend metrics."""
        return self.backend.load(timestamp)

    def list_trend_timestamps(self) -> List[str]:
        """List all trend timestamps."""
        return self.backend.list_keys()


