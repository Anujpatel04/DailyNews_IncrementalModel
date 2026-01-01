"""LLM-based summarization for clusters and daily reports."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from incremental_news_intelligence.config.settings import LLMConfig
from incremental_news_intelligence.storage.managers import (
    ClusterStorage,
    ProcessedArticleStorage,
    TopicStorage,
)

logger = logging.getLogger(__name__)

class LLMClient:
    """Abstract LLM client interface."""

    def generate(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """Generate text from prompt."""
        raise NotImplementedError

class OpenAIClient(LLMClient):
    """OpenAI API client."""

    def __init__(self, config: LLMConfig):
        """Initialize OpenAI client."""
        self.config = config
        try:
            import openai
            self.client = openai.OpenAI(api_key=config.api_key)
        except ImportError:
            logger.error("openai package not installed")
            self.client = None

    def generate(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """Generate text using OpenAI API."""
        if not self.client:
            logger.error("OpenAI client not initialized")
            return None

        try:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return None

class ClusterSummarizer:
    """Generate summaries for clusters using LLMs."""

    def __init__(
        self,
        llm_config: LLMConfig,
        cluster_storage: ClusterStorage,
        processed_storage: ProcessedArticleStorage,
        topic_storage: TopicStorage,
    ):
        """Initialize cluster summarizer."""
        self.cluster_storage = cluster_storage
        self.processed_storage = processed_storage
        self.topic_storage = topic_storage

        if llm_config.provider == "openai":
            self.llm_client = OpenAIClient(llm_config)
        else:
            logger.warning(f"Unknown LLM provider: {llm_config.provider}")
            self.llm_client = None

    def _get_cluster_articles(self, cluster_id: str) -> List[Dict[str, Any]]:
        """Get processed articles for cluster."""
        cluster = self.cluster_storage.load_cluster(cluster_id)
        if not cluster:
            return []

        article_ids = cluster.get("article_ids", [])
        articles = []
        for article_id in article_ids[:10]:
            article = self.processed_storage.load_processed_article(article_id)
            if article:
                articles.append(article)

        return articles

    def _build_cluster_prompt(
        self, cluster_id: str, articles: List[Dict[str, Any]], topics: Dict[str, Any]
    ) -> str:
        """Build prompt for cluster summarization."""
        top_keywords = topics.get("top_keywords", [])
        keywords_str = ", ".join([kw["keyword"] for kw in top_keywords[:5]])

        article_titles = [a.get("title", "") for a in articles[:5]]
        titles_str = "\n".join(f"- {title}" for title in article_titles if title)

        prompt = f"""Summarize the following news cluster in 2-3 sentences.

Cluster ID: {cluster_id}
Number of articles: {len(articles)}
Key topics: {keywords_str}

Sample article titles:
{titles_str}

Provide a concise summary of what this cluster is about:"""

        return prompt

    def summarize_cluster(self, cluster_id: str) -> Optional[str]:
        """
        Generate summary for cluster.

        Args:
            cluster_id: Cluster to summarize

        Returns:
            Summary text or None if generation fails
        """
        if not self.llm_client:
            logger.warning("LLM client not available")
            return None

        articles = self._get_cluster_articles(cluster_id)
        if not articles:
            logger.warning(f"No articles found for cluster {cluster_id}")
            return None

        topics = self.topic_storage.load_topic_stats(cluster_id) or {}
        prompt = self._build_cluster_prompt(cluster_id, articles, topics)

        summary = self.llm_client.generate(prompt, max_tokens=200)
        if summary:
            cluster = self.cluster_storage.load_cluster(cluster_id)
            if cluster:
                cluster["summary"] = summary
                cluster["summary_updated_at"] = datetime.utcnow().isoformat()
                self.cluster_storage.save_cluster(cluster_id, cluster)

        return summary

    def summarize_all_clusters(self) -> Dict[str, str]:
        """Generate summaries for all clusters."""
        cluster_ids = self.cluster_storage.list_cluster_ids()
        summaries = {}

        for cluster_id in cluster_ids:
            cluster = self.cluster_storage.load_cluster(cluster_id)
            if cluster and cluster.get("summary"):
                continue

            summary = self.summarize_cluster(cluster_id)
            if summary:
                summaries[cluster_id] = summary

        logger.info(f"Generated {len(summaries)} cluster summaries")
        return summaries

class DailyReportGenerator:
    """Generate daily "what changed" reports."""

    def __init__(
        self,
        llm_config: LLMConfig,
        cluster_storage: ClusterStorage,
        trend_storage: TrendStorage,
    ):
        """Initialize daily report generator."""
        self.cluster_storage = cluster_storage
        self.trend_storage = trend_storage

        if llm_config.provider == "openai":
            self.llm_client = OpenAIClient(llm_config)
        else:
            logger.warning(f"Unknown LLM provider: {llm_config.provider}")
            self.llm_client = None

    def generate_daily_summary(self, date: Optional[str] = None) -> Optional[str]:
        """
        Generate daily summary report.

        Args:
            date: Date string (ISO format), defaults to today

        Returns:
            Daily summary text
        """
        if not self.llm_client:
            logger.warning("LLM client not available")
            return None

        if date is None:
            date = datetime.utcnow().isoformat()[:10]

        trend_metrics = self.trend_storage.load_trend_metrics(date)
        if not trend_metrics:
            logger.warning(f"No trend metrics found for {date}")
            return None

        growing = trend_metrics.get("growing_clusters", [])
        new_clusters = trend_metrics.get("new_clusters", [])
        declining = trend_metrics.get("declining_clusters", [])

        cluster_details = []
        for cluster_info in (growing + new_clusters)[:5]:
            cluster_id = cluster_info.get("cluster_id")
            if cluster_id:
                cluster = self.cluster_storage.load_cluster(cluster_id)
                if cluster:
                    summary = cluster.get("summary", "No summary available")
                    cluster_details.append(
                        f"Cluster {cluster_id}: {summary} "
                        f"({cluster_info.get('document_count', 0)} articles)"
                    )

        prompt = f"""Generate a daily news intelligence report for {date}.

Key changes:
- {len(growing)} clusters showing rapid growth
- {len(new_clusters)} new clusters emerging
- {len(declining)} clusters declining

Top clusters:
{chr(10).join(cluster_details[:5])}

Provide a 3-4 sentence summary of the day's key developments:"""

        summary = self.llm_client.generate(prompt, max_tokens=300)
        return summary
