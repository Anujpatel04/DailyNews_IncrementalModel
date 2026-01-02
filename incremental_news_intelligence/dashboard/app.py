"""Flask dashboard application."""
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

    llm_client = None
    if config.llm.api_key:
        llm_client = OpenAIClient(config.llm)

    def extract_keywords(text: str) -> List[str]:
        """Extract keywords from text for searching."""
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'what', 'when', 'where', 'who', 'why', 'how', 'this', 'that', 'these', 'those'}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        return keywords[:10]

    def find_relevant_data(question: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
        """
        Search through clusters and articles to find relevant information.
        
        Returns:
            Tuple of (relevant_articles, relevant_clusters, has_relevant_data)
        """
        question_lower = question.lower()
        keywords = extract_keywords(question)
        
        relevant_articles = []
        relevant_clusters = []
        
        all_article_ids = processed_storage.list_article_ids()
        for article_id in all_article_ids[:100]:
            article = processed_storage.load_processed_article(article_id)
            if not article:
                continue
            
            article_text = (
                article.get("title", "") + " " + 
                article.get("text", "") + " " + 
                article.get("description", "")
            ).lower()
            
            keyword_matches = sum(1 for kw in keywords if kw in article_text)
            direct_match = any(kw in article_text for kw in keywords) if keywords else False
            
            if keyword_matches >= 2 or any(kw in article_text for kw in keywords[:3]):
                relevant_articles.append({
                    "title": article.get("title", ""),
                    "snippet": (article.get("description", "") or article.get("text", ""))[:300],
                    "source": article.get("source", ""),
                    "date": article.get("published_date", ""),
                    "text": article.get("text", "")[:500],
                    "url": article.get("url", "")
                })
                
                if len(relevant_articles) >= 15:
                    break
        
        cluster_ids = cluster_storage.list_cluster_ids()
        for cluster_id in cluster_ids:
            cluster = cluster_storage.load_cluster(cluster_id)
            if not cluster:
                continue
            
            cluster_text = ""
            summary = cluster.get("summary", "")
            if summary:
                cluster_text += summary.lower() + " "
            
            topic_stats = topic_storage.load_topic_stats(cluster_id)
            if topic_stats:
                top_keywords = topic_stats.get("top_keywords", [])
                for kw_data in top_keywords[:5]:
                    keyword = kw_data.get("keyword", "").lower()
                    cluster_text += keyword + " "
            
            keyword_matches = sum(1 for kw in keywords if kw in cluster_text) if keywords else 0
            direct_match = any(kw in cluster_text for kw in keywords) if keywords else False
            
            if keyword_matches >= 1 or direct_match:
                relevant_clusters.append({
                    "cluster_id": cluster_id,
                    "summary": summary,
                    "topic_stats": topic_stats,
                    "article_count": len(cluster.get("article_ids", []))
                })
                
                if len(relevant_clusters) >= 10:
                    break
        
        has_relevant_data = len(relevant_articles) > 0 or len(relevant_clusters) > 0
        
        return relevant_articles, relevant_clusters, has_relevant_data

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
                "error": "LLM not configured. Please set OPENAI_API_KEY or AZURE_OPENAI_API_KEY in .env file."
            }), 400

        data = request.get_json()
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"error": "Question is required"}), 400

        try:
            relevant_articles, relevant_clusters, has_relevant_data = find_relevant_data(question)
            
            if not has_relevant_data:
                return jsonify({
                    "answer": "I don't have information about this topic in my clusters. Please try asking about topics related to the news articles I have ingested.",
                    "sources_count": 0,
                    "info_found": False
                })

            articles_context_parts = []
            for idx, article in enumerate(relevant_articles[:10], 1):
                article_url = article.get("url", "")
                articles_context_parts.append(
                    f"[Source {idx}] Title: {article['title']}\n"
                    f"Content: {article['snippet']}\n"
                    f"Source: {article['source']}\n"
                    f"Date: {article['date']}\n"
                    f"URL: {article_url}\n"
                )
            articles_context = "\n".join(articles_context_parts)

            clusters_context_parts = []
            for cluster in relevant_clusters[:5]:
                summary = cluster.get("summary", "")
                cluster_id = cluster.get("cluster_id", "")
                topic_stats = cluster.get("topic_stats", {})
                top_keywords = topic_stats.get("top_keywords", [])
                keywords_str = ", ".join([kw.get("keyword", "") for kw in top_keywords[:5]])
                
                cluster_text = f"Cluster {cluster_id}: {summary}"
                if keywords_str:
                    cluster_text += f" (Keywords: {keywords_str})"
                clusters_context_parts.append(cluster_text)
            
            clusters_context = "\n".join(clusters_context_parts) if clusters_context_parts else "No relevant cluster summaries available."

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

            prompt = f"""You are a professional news intelligence analyst. Provide a comprehensive, well-structured answer based ONLY on the information provided below from the ingested news articles and clusters.

{trends_info}

Relevant News Articles:
{articles_context}

Relevant Topic Clusters:
{clusters_context}

User Question: {question}

FORMATTING INSTRUCTIONS:
1. Use professional markdown formatting:
   - Use **bold** for key terms, company names, product names, and important concepts
   - Use bullet points (-) for main points
   - Use sub-bullets or numbered lists when appropriate
   - Use clear section headers if the answer is long

2. Structure your response professionally:
   - Start with a brief summary or overview if the question is complex
   - Organize information logically by topic or theme
   - Use clear, concise language
   - Provide context and explanations, not just facts

3. Source citations:
   - Cite sources inline using [Source X] format after each fact or claim
   - Multiple sources should be cited as [Source X, Source Y]
   - Always cite sources for specific facts, statistics, or claims

4. Content guidelines:
   - Answer ONLY based on the information provided above
   - If information is insufficient, clearly state what you can and cannot answer
   - Provide detailed explanations and context, not just bullet points
   - Use professional business/technical language appropriate for news analysis
   - Connect related information to provide comprehensive insights

5. Response structure example:
   **Overview:** Brief summary of the topic

   **Key Points:**
   - **Main Point 1:** Detailed explanation with context [Source 1]
     - Supporting detail or sub-point [Source 2]
   - **Main Point 2:** Detailed explanation with context [Source 3, Source 4]

   **Analysis:** Additional insights or connections between points

Remember: Be thorough, professional, and provide value through clear explanations and context."""

            answer = llm_client.generate(prompt, max_tokens=1500)

            if not answer:
                return jsonify({"error": "Failed to generate response"}), 500

            sources_list = []
            for idx, article in enumerate(relevant_articles[:10], 1):
                sources_list.append({
                    "id": idx,
                    "title": article.get("title", ""),
                    "source": article.get("source", ""),
                    "date": article.get("date", ""),
                    "url": article.get("url", "")
                })

            return jsonify({
                "answer": answer,
                "sources": sources_list,
                "sources_count": len(relevant_articles),
                "clusters_count": len(relevant_clusters),
                "info_found": True
            })

        except Exception as e:
            logger.error(f"Error in chat endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    return app
