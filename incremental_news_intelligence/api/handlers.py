"""API request handlers (no business logic)."""
import logging
from typing import Any, Dict, List, Optional

from incremental_news_intelligence.storage.managers import (
    ClusterStorage,
    ProcessedArticleStorage,
    TrendStorage,
)

logger = logging.getLogger(__name__)

class APIHandlers:
    """Read-only API handlers."""

    def __init__(
        self,
        cluster_storage: ClusterStorage,
        processed_storage: ProcessedArticleStorage,
        trend_storage: TrendStorage,
    ):
        """Initialize API handlers."""
        self.cluster_storage = cluster_storage
        self.processed_storage = processed_storage
        self.trend_storage = trend_storage

    def get_clusters(self) -> List[Dict[str, Any]]:
        """Get all clusters."""
        clusters = []
        for cluster_id in self.cluster_storage.list_cluster_ids():
            cluster = self.cluster_storage.load_cluster(cluster_id)
            if cluster:
                clusters.append(cluster)
        return clusters

    def get_cluster(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get single cluster by ID."""
        return self.cluster_storage.load_cluster(cluster_id)

    def get_trends(self, limit: int = 10) -> Dict[str, Any]:
        """Get latest trend metrics."""
        timestamps = self.trend_storage.list_trend_timestamps()
        if not timestamps:
            return {"error": "No trend data available"}

        latest_timestamp = sorted(timestamps)[-1]
        trends = self.trend_storage.load_trend_metrics(latest_timestamp)
        if not trends:
            return {"error": "Trend data not found"}

        return {
            "timestamp": trends.get("timestamp"),
            "total_clusters": trends.get("total_clusters", 0),
            "growing_clusters": trends.get("growing_clusters", [])[:limit],
            "new_clusters": trends.get("new_clusters", [])[:limit],
            "declining_clusters": trends.get("declining_clusters", [])[:limit],
        }

    def get_articles_by_cluster(
        self, cluster_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get articles for cluster."""
        cluster = self.cluster_storage.load_cluster(cluster_id)
        if not cluster:
            return []

        article_ids = cluster.get("article_ids", [])[:limit]
        articles = []
        for article_id in article_ids:
            article = self.processed_storage.load_processed_article(article_id)
            if article:
                articles.append(article)

        return articles

    def get_daily_summary(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get daily summary (requires reasoning layer to generate)."""
        if date is None:
            from datetime import datetime
            date = datetime.utcnow().isoformat()[:10]

        trends = self.trend_storage.load_trend_metrics(date)
        if not trends:
            return {"error": f"No data available for {date}"}

        return {
            "date": date,
            "summary": "Use reasoning layer to generate summary",
            "trends": trends,
        }


