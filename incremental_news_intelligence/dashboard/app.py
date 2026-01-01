"""Flask dashboard application."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request

from incremental_news_intelligence.config.settings import SystemConfig
from incremental_news_intelligence.reasoning.summarizer import OpenAIClient
from incremental_news_intelligence.storage.managers import (
    ClusterStorage,
    EmbeddingStorage,
    ProcessedArticleStorage,
    TopicStorage,
    TrendStorage,
)

logger = logging.getLogger(__name__)


def create_dashboard_app(config: SystemConfig) -> Flask:
    """Create Flask dashboard application."""
    import os
    dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(dashboard_dir, "templates"),
        static_folder=os.path.join(dashboard_dir, "static")
    )
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    storage_config = config.storage
    cluster_storage = ClusterStorage(storage_config)
    processed_storage = ProcessedArticleStorage(storage_config)
    embedding_storage = EmbeddingStorage(storage_config)
    topic_storage = TopicStorage(storage_config)
    trend_storage = TrendStorage(storage_config)
    
    # Initialize LLM client for chatbot
    llm_client = None
    if config.llm.api_key:
        llm_client = OpenAIClient(config.llm)

    @app.route("/")
    def index() -> str:
        """Dashboard home page."""
        return render_template("index.html")

    @app.route("/api/trends")
    def api_trends() -> Dict[str, Any]:
        """Get latest trends."""
        timestamps = trend_storage.list_trend_timestamps()
        if not timestamps:
            return jsonify({"error": "No trend data available"})

        latest_timestamp = sorted(timestamps)[-1]
        trends = trend_storage.load_trend_metrics(latest_timestamp)
        return jsonify(trends or {"error": "Trend data not found"})

    @app.route("/api/clusters")
    def api_clusters() -> Dict[str, Any]:
        """Get all clusters."""
        cluster_ids = cluster_storage.list_cluster_ids()
        clusters = []
        for cluster_id in cluster_ids:
            cluster = cluster_storage.load_cluster(cluster_id)
            if cluster:
                topic_stats = topic_storage.load_topic_stats(cluster_id)
                cluster["topic_stats"] = topic_stats
                clusters.append(cluster)

        return jsonify({"clusters": clusters, "count": len(clusters)})

    @app.route("/api/clusters/<cluster_id>")
    def api_cluster_detail(cluster_id: str) -> Dict[str, Any]:
        """Get cluster details with articles."""
        cluster = cluster_storage.load_cluster(cluster_id)
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        article_ids = cluster.get("article_ids", [])
        articles = []
        for article_id in article_ids[:50]:
            article = processed_storage.load_processed_article(article_id)
            if article:
                articles.append(article)

        topic_stats = topic_storage.load_topic_stats(cluster_id)

        return jsonify({
            "cluster": cluster,
            "articles": articles,
            "topic_stats": topic_stats,
        })

    @app.route("/api/articles")
    def api_articles() -> Dict[str, Any]:
        """Get articles with optional cluster filter."""
        cluster_id = request.args.get("cluster_id")
        limit = int(request.args.get("limit", 50))

        if cluster_id:
            cluster = cluster_storage.load_cluster(cluster_id)
            if not cluster:
                return jsonify({"error": "Cluster not found"}), 404
            article_ids = cluster.get("article_ids", [])[:limit]
        else:
            article_ids = processed_storage.list_article_ids()[:limit]

        articles = []
        for article_id in article_ids:
            article = processed_storage.load_processed_article(article_id)
            if article:
                metadata = embedding_storage.get_metadata(article_id)
                article["cluster_id"] = metadata.get("cluster_id") if metadata else None
                articles.append(article)

        return jsonify({"articles": articles, "count": len(articles)})

    @app.route("/api/stats")
    def api_stats() -> Dict[str, Any]:
        """Get system statistics."""
        return jsonify({
            "total_articles": len(processed_storage.list_article_ids()),
            "total_clusters": len(cluster_storage.list_cluster_ids()),
            "total_embeddings": len(embedding_storage.list_article_ids()),
        })

    @app.route("/api/search")
    def api_search() -> Dict[str, Any]:
        """Search articles by text."""
        query = request.args.get("q", "").lower()
        if not query:
            return jsonify({"articles": [], "count": 0})

        all_article_ids = processed_storage.list_article_ids()
        matching_articles = []

        for article_id in all_article_ids:
            article = processed_storage.load_processed_article(article_id)
            if not article:
                continue

            text = (
                article.get("title", "") + " " + article.get("text", "")
            ).lower()

            if query in text:
                metadata = embedding_storage.get_metadata(article_id)
                article["cluster_id"] = metadata.get("cluster_id") if metadata else None
                matching_articles.append(article)

                if len(matching_articles) >= 50:
                    break

        return jsonify({"articles": matching_articles, "count": len(matching_articles)})

    @app.route("/api/chat", methods=["POST"])
    def api_chat() -> Dict[str, Any]:
        """Chatbot endpoint that answers questions about news."""
        if not llm_client:
            return jsonify({
                "error": "LLM not configured. Please set OPENAI_API_KEY in .env file."
            }), 400

        data = request.get_json()
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"error": "Question is required"}), 400

        try:
            # Get recent articles and trends for context
            recent_articles = []
            article_ids = processed_storage.list_article_ids()[:20]
            for article_id in article_ids:
                article = processed_storage.load_processed_article(article_id)
                if article:
                    recent_articles.append({
                        "title": article.get("title", ""),
                        "snippet": (article.get("description", "") or article.get("text", ""))[:200],
                        "source": article.get("source", ""),
                        "date": article.get("published_date", "")
                    })

            # Get latest trends
            timestamps = trend_storage.list_trend_timestamps()
            trends_info = ""
            if timestamps:
                latest_timestamp = sorted(timestamps)[-1]
                trends = trend_storage.load_trend_metrics(latest_timestamp)
                if trends:
                    trends_info = f"""
Current Trends:
- Total clusters: {trends.get('total_clusters', 0)}
- Growing clusters: {len(trends.get('growing_clusters', []))}
- New clusters: {len(trends.get('new_clusters', []))}
- Declining clusters: {len(trends.get('declining_clusters', []))}
"""

            # Get top clusters with summaries
            cluster_summaries = []
            cluster_ids = cluster_storage.list_cluster_ids()[:10]
            for cluster_id in cluster_ids:
                cluster = cluster_storage.load_cluster(cluster_id)
                if cluster:
                    summary = cluster.get("summary", "")
                    if summary:
                        cluster_summaries.append(f"- {cluster_id}: {summary}")

            # Build context for LLM
            articles_context = "\n".join([
                f"Title: {a['title']}\nSnippet: {a['snippet']}\nSource: {a['source']}\n"
                for a in recent_articles[:10]
            ])

            clusters_context = "\n".join(cluster_summaries[:5]) if cluster_summaries else "No cluster summaries available yet."

            prompt = f"""You are a helpful news intelligence assistant. Answer questions based on the following recent news articles and trends.

{trends_info}

Recent News Articles:
{articles_context}

Topic Clusters:
{clusters_context}

User Question: {question}

Provide a helpful, accurate answer based on the information above. If the question cannot be answered from the provided context, say so. Keep your answer concise but informative (2-4 sentences)."""

            answer = llm_client.generate(prompt, max_tokens=500)
            
            if not answer:
                return jsonify({"error": "Failed to generate response"}), 500

            return jsonify({
                "answer": answer,
                "sources_count": len(recent_articles)
            })

        except Exception as e:
            logger.error(f"Error in chat endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    return app

