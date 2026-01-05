"""Flask API server."""
import logging
from typing import Any, Dict

from flask import Flask, jsonify, request

from incremental_news_intelligence.api.handlers import APIHandlers
from incremental_news_intelligence.storage.managers import (
    ClusterStorage,
    ProcessedArticleStorage,
    TrendStorage,
)

logger = logging.getLogger(__name__)

def create_app(
    cluster_storage: ClusterStorage,
    processed_storage: ProcessedArticleStorage,
    trend_storage: TrendStorage,
) -> Flask:
    """Create Flask application."""
    app = Flask(__name__)
    handlers = APIHandlers(cluster_storage, processed_storage, trend_storage)

    @app.route("/clusters", methods=["GET"])
    def get_clusters() -> Dict[str, Any]:
        """Get all clusters."""
        clusters = handlers.get_clusters()
        return jsonify({"clusters": clusters, "count": len(clusters)})

    @app.route("/clusters/<cluster_id>", methods=["GET"])
    def get_cluster(cluster_id: str) -> Dict[str, Any]:
        """Get single cluster."""
        cluster = handlers.get_cluster(cluster_id)
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404
        return jsonify(cluster)

    @app.route("/trends", methods=["GET"])
    def get_trends() -> Dict[str, Any]:
        """Get latest trends."""
        limit = request.args.get("limit", 10, type=int)
        trends = handlers.get_trends(limit=limit)
        return jsonify(trends)

    @app.route("/articles", methods=["GET"])
    def get_articles() -> Dict[str, Any]:
        """Get articles by cluster ID."""
        cluster_id = request.args.get("cluster_id")
        if not cluster_id:
            return jsonify({"error": "cluster_id parameter required"}), 400

        limit = request.args.get("limit", 50, type=int)
        articles = handlers.get_articles_by_cluster(cluster_id, limit=limit)
        return jsonify({"articles": articles, "count": len(articles)})

    @app.route("/daily-summary", methods=["GET"])
    def get_daily_summary() -> Dict[str, Any]:
        """Get daily summary."""
        date = request.args.get("date")
        summary = handlers.get_daily_summary(date=date)
        return jsonify(summary)

    @app.route("/health", methods=["GET"])
    def health() -> Dict[str, str]:
        """Health check endpoint."""
        return jsonify({"status": "healthy"})

    return app






