"""NewsAPI.ai client with rate limiting and retries."""
import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from incremental_news_intelligence.config.settings import NewsAPIAIConfig
from incremental_news_intelligence.ingestion.bing_client import RateLimiter

logger = logging.getLogger(__name__)

class NewsAPIAIClient:
    """Client for NewsAPI.ai."""

    def __init__(self, config: NewsAPIAIConfig):
        """Initialize NewsAPI.ai client."""
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)
        self.session = requests.Session()

    def _generate_article_id(self, article: Dict[str, Any]) -> str:
        """Generate deterministic article ID from URL or link."""
        url = article.get("url") or article.get("link", "") or article.get("source_url", "")
        if not url:
            logger.warning(f"Article missing URL/link: {article.get('title', 'Unknown')}")
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _make_request(
        self, params: Dict[str, Any], retry_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Make API request with retries and exponential backoff."""
        self.rate_limiter.wait_if_needed()

        try:
            response = self.session.get(
                self.config.endpoint, params=params, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if retry_count < self.config.max_retries:
                backoff_time = (
                    self.config.retry_backoff_base ** retry_count
                )
                logger.warning(
                    f"Request failed (attempt {retry_count + 1}): {e}. "
                    f"Retrying in {backoff_time}s"
                )
                time.sleep(backoff_time)
                return self._make_request(params, retry_count + 1)
            else:
                logger.error(f"Request failed after {self.config.max_retries} retries: {e}")
                raise

    def search(
        self,
        query: str,
        engine: str = "google_news",
        count: Optional[int] = None,
        offset: int = 0,
        freshness: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search using NewsAPI.ai.

        Args:
            query: Search query string
            engine: Search engine (google_news, etc.)
            count: Number of results (max 100)
            offset: Pagination offset
            freshness: Date filter (e.g., "day", "week", "month")

        Returns:
            List of article dictionaries with generated IDs
        """
        num_results = count or min(self.config.max_results_per_query, 50)
        
        params = {
            "engine": engine,
            "q": query,
            "num": num_results,
            "apiKey": self.config.api_key,
        }

        if freshness:
            params["freshness"] = freshness

        logger.info(f"Searching {engine} via NewsAPI.ai: query='{query}', num={num_results}")

        try:
            response_data = self._make_request(params)
            if not response_data:
                return []

            articles = response_data.get("organic_results", [])
            if not articles:
                articles = response_data.get("news_results", [])
            if not articles:
                articles = response_data.get("articles", [])
            if not articles:
                articles = response_data.get("results", [])

            if not articles:
                logger.warning(f"No articles found in response. Response keys: {list(response_data.keys())}")
                return []

            logger.info(f"Retrieved {len(articles)} articles from NewsAPI.ai")

            enriched_articles = []
            for article in articles:
                article_id = self._generate_article_id(article)
                article["_article_id"] = article_id
                article["_ingestion_query"] = query
                article["_ingestion_engine"] = f"newsapi_ai_{engine}"
                article["_ingestion_offset"] = offset
                enriched_articles.append(article)

            return enriched_articles

        except Exception as e:
            logger.error(f"Error in NewsAPI.ai search: {e}")
            return []

    def search_with_pagination(
        self,
        query: str,
        engine: str = "google_news",
        max_articles: Optional[int] = None,
        freshness: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search with automatic pagination.

        Args:
            query: Search query string
            engine: Search engine
            max_articles: Maximum number of articles to retrieve
            freshness: Date filter

        Returns:
            List of all retrieved articles
        """
        if max_articles:
            count = min(max_articles, self.config.max_results_per_query)
        else:
            count = self.config.max_results_per_query

        articles = self.search(
            query=query,
            engine=engine,
            count=count,
            offset=0,
            freshness=freshness,
        )

        if max_articles and len(articles) > max_articles:
            articles = articles[:max_articles]

        logger.info(f"Total articles retrieved from NewsAPI.ai {engine}: {len(articles)}")
        return articles






