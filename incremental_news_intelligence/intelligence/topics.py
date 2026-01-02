"""Incremental topic modeling with time decay."""
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List

from incremental_news_intelligence.config.settings import TopicModelingConfig
from incremental_news_intelligence.storage.managers import (
    ClusterStorage,
    ProcessedArticleStorage,
    TopicStorage,
)

logger = logging.getLogger(__name__)

class IncrementalTopicModeler:
    """Maintains rolling keyword statistics per cluster with time decay."""

    def __init__(
        self,
        config: TopicModelingConfig,
        cluster_storage: ClusterStorage,
        processed_storage: ProcessedArticleStorage,
        topic_storage: TopicStorage,
    ):
        """Initialize topic modeler."""
        self.config = config
        self.cluster_storage = cluster_storage
        self.processed_storage = processed_storage
        self.topic_storage = topic_storage

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (simple word-based)."""
        words = text.lower().split()
        filtered_words = [
            w
            for w in words
            if len(w) > 3 and w.isalpha()
        ]
        return filtered_words

    def _apply_time_decay(
        self, keyword_counts: Dict[str, float], last_update: datetime
    ) -> Dict[str, float]:
        """Apply time decay to keyword counts."""
        now = datetime.utcnow()
        hours_elapsed = (now - last_update).total_seconds() / 3600
        decay_factor = self.config.time_decay_factor ** hours_elapsed

        return {k: v * decay_factor for k, v in keyword_counts.items()}

    def _update_cluster_topics(
        self, cluster_id: str, article_id: str
    ) -> None:
        """Update topic statistics for cluster with new article."""
        processed_article = self.processed_storage.load_processed_article(article_id)
        if not processed_article:
            return

        text = processed_article.get("text", "")
        keywords = self._extract_keywords(text)

        existing_stats = self.topic_storage.load_topic_stats(cluster_id)
        if existing_stats:
            keyword_counts = existing_stats.get("keyword_counts", {})
            last_update_str = existing_stats.get("_last_updated")
            if last_update_str:
                last_update = datetime.fromisoformat(last_update_str)
                keyword_counts = self._apply_time_decay(keyword_counts, last_update)
        else:
            keyword_counts = {}

        keyword_counter = Counter(keywords)
        for keyword, count in keyword_counter.items():
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + count

        filtered_counts = {
            k: v
            for k, v in keyword_counts.items()
            if v >= self.config.min_keyword_frequency
        }

        top_keywords = sorted(
            filtered_counts.items(), key=lambda x: x[1], reverse=True
        )[: self.config.top_keywords_per_cluster]

        topic_stats = {
            "cluster_id": cluster_id,
            "keyword_counts": filtered_counts,
            "top_keywords": [{"keyword": k, "frequency": v} for k, v in top_keywords],
            "total_keywords": len(filtered_counts),
        }

        self.topic_storage.save_topic_stats(cluster_id, topic_stats)

    def update_topics_for_cluster(self, cluster_id: str) -> None:
        """Update topic statistics for all articles in cluster."""
        cluster = self.cluster_storage.load_cluster(cluster_id)
        if not cluster:
            return

        article_ids = cluster.get("article_ids", [])
        for article_id in article_ids:
            self._update_cluster_topics(cluster_id, article_id)

        logger.debug(f"Updated topics for cluster {cluster_id}")

    def update_all_cluster_topics(self) -> None:
        """Update topic statistics for all clusters."""
        cluster_ids = self.cluster_storage.list_cluster_ids()
        for cluster_id in cluster_ids:
            self.update_topics_for_cluster(cluster_id)

        logger.info(f"Updated topics for {len(cluster_ids)} clusters")

