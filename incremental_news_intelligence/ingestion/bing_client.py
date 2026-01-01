"""Bing News Search API client with rate limiting and retries."""
import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from incremental_news_intelligence.config.settings import BingNewsConfig

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int):
        """Initialize rate limiter."""
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time: Optional[float] = None

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limit."""
        if self.last_call_time is None:
            self.last_call_time = time.time()
            return

        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_call_time = time.time()

class BingNewsClient:
    """Client for SearchAPI Bing News Search."""

    def __init__(self, config: BingNewsConfig):
        """Initialize SearchAPI client."""
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
        })

    def _generate_article_id(self, article: Dict[str, Any]) -> str:
        """Generate deterministic article ID from URL or link."""
        url = article.get("url") or article.get("link", "")
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
        count: Optional[int] = None,
        offset: int = 0,
        freshness: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for news articles using SearchAPI.

        Args:
            query: Search query string
            count: Number of results (max 100)
            offset: Pagination offset (not directly supported by SearchAPI)
            freshness: Date filter (e.g., "day", "week", "month")
            sort_by: Sort order (ignored for SearchAPI)

        Returns:
            List of article dictionaries with generated IDs
        """
        num_results = count or min(self.config.max_results_per_query, 50)

        params = {
            "engine": "bing_news",
            "q": query,
            "num": num_results,
        }

        if freshness:
            params["freshness"] = freshness

        logger.info(f"Searching Bing News via SearchAPI: query='{query}', num={num_results}")

        try:
            response_data = self._make_request(params)
            if not response_data:
                return []

            articles = response_data.get("organic_results", [])
            if not articles:
                articles = response_data.get("news_results", [])
            if not articles:
                articles = response_data.get("value", [])
            if not articles:
                articles = response_data.get("news", [])

            if not articles:
                logger.warning(f"No articles found in response. Response keys: {list(response_data.keys())}")
                return []

            logger.info(f"Retrieved {len(articles)} articles")

            enriched_articles = []
            for article in articles:
                article_id = self._generate_article_id(article)
                article["_article_id"] = article_id
                article["_ingestion_query"] = query
                article["_ingestion_offset"] = offset
                enriched_articles.append(article)

            return enriched_articles

        except Exception as e:
            logger.error(f"Error in search: {e}")
            return []

    def search_with_pagination(
        self,
        query: str,
        max_articles: Optional[int] = None,
        freshness: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search with automatic pagination.

        Args:
            query: Search query string
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
            count=count,
            offset=0,
            freshness=freshness,
        )

        if max_articles and len(articles) > max_articles:
            articles = articles[:max_articles]

        logger.info(f"Total articles retrieved: {len(articles)}")
        return articles
