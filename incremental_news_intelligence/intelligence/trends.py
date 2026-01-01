"""Trend and drift detection."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from incremental_news_intelligence.config.settings import TrendDetectionConfig
from incremental_news_intelligence.storage.managers import ClusterStorage, TrendStorage

logger = logging.getLogger(__name__)

class TrendDetector:
    """Detects trends: growing clusters, new clusters, declining clusters."""

    def __init__(
        self,
        config: TrendDetectionConfig,
        cluster_storage: ClusterStorage,
        trend_storage: TrendStorage,
    ):
        """Initialize trend detector."""
        self.config = config
        self.cluster_storage = cluster_storage
        self.trend_storage = trend_storage

    def _get_cluster_growth_rate(
        self, cluster: Dict[str, Any], previous_count: int
    ) -> float:
        """Compute growth rate for cluster."""
        current_count = cluster.get("document_count", 0)
        if previous_count == 0:
            return float("inf") if current_count > 0 else 0.0
        return current_count / previous_count

    def detect_trends(self) -> Dict[str, Any]:
        """
        Detect trends across all clusters.

        Returns:
            Dictionary with trend metrics
        """
        all_clusters = self.cluster_storage.get_all_clusters()
        now = datetime.utcnow()
        new_cluster_window = timedelta(hours=self.config.new_cluster_window_hours)

        growing_clusters = []
        new_clusters = []
        declining_clusters = []
        stable_clusters = []

        previous_trends = self._load_previous_trends()

        for cluster_id, cluster in all_clusters.items():
            created_at_str = cluster.get("created_at")
            if not created_at_str:
                continue

            created_at = datetime.fromisoformat(created_at_str)
            is_new = (now - created_at) < new_cluster_window

            document_count = cluster.get("document_count", 0)
            last_updated_str = cluster.get("last_updated")
            last_updated = (
                datetime.fromisoformat(last_updated_str)
                if last_updated_str
                else created_at
            )

            previous_count = (
                previous_trends.get(cluster_id, {}).get("document_count", 0)
                if previous_trends
                else 0
            )

            growth_rate = self._get_cluster_growth_rate(cluster, previous_count)

            cluster_trend = {
                "cluster_id": cluster_id,
                "document_count": document_count,
                "growth_rate": growth_rate,
                "created_at": created_at_str,
                "last_updated": last_updated_str,
            }

            if is_new:
                new_clusters.append(cluster_trend)
            elif growth_rate >= self.config.growth_threshold:
                growing_clusters.append(cluster_trend)
            elif growth_rate <= self.config.decline_threshold and document_count > 0:
                declining_clusters.append(cluster_trend)
            else:
                stable_clusters.append(cluster_trend)

        trend_metrics = {
            "timestamp": now.isoformat(),
            "total_clusters": len(all_clusters),
            "growing_clusters": sorted(
                growing_clusters, key=lambda x: x["growth_rate"], reverse=True
            )[:10],
            "new_clusters": sorted(
                new_clusters, key=lambda x: x["document_count"], reverse=True
            )[:10],
            "declining_clusters": sorted(
                declining_clusters, key=lambda x: x["growth_rate"]
            )[:10],
            "stable_clusters_count": len(stable_clusters),
        }

        self.trend_storage.save_trend_metrics(now.isoformat(), trend_metrics)
        logger.info(f"Detected trends: {len(growing_clusters)} growing, "
                   f"{len(new_clusters)} new, {len(declining_clusters)} declining")

        return trend_metrics

    def _load_previous_trends(self) -> Dict[str, Dict[str, Any]]:
        """Load previous trend metrics for comparison."""
        timestamps = self.trend_storage.list_trend_timestamps()
        if not timestamps:
            return {}

        latest_timestamp = sorted(timestamps)[-1]
        previous_trends = self.trend_storage.load_trend_metrics(latest_timestamp)
        if not previous_trends:
            return {}

        cluster_data = {}
        for trend_type in ["growing_clusters", "new_clusters", "declining_clusters"]:
            clusters = previous_trends.get(trend_type, [])
            for cluster in clusters:
                cluster_id = cluster.get("cluster_id")
                if cluster_id:
                    cluster_data[cluster_id] = cluster

        all_clusters = self.cluster_storage.get_all_clusters()
        for cluster_id, cluster in all_clusters.items():
            if cluster_id not in cluster_data:
                cluster_data[cluster_id] = {
                    "cluster_id": cluster_id,
                    "document_count": cluster.get("document_count", 0),
                }

        return cluster_data
