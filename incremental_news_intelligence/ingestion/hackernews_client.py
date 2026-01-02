"""Hacker News API client with rate limiting."""
import hashlib
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from incremental_news_intelligence.ingestion.bing_client import RateLimiter

logger = logging.getLogger(__name__)

class HackerNewsClient:
    """Client for Hacker News API."""

    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self, enabled: bool = True, rate_limit_per_minute: int = 60):
        """Initialize Hacker News client."""
        self.enabled = enabled
        self.rate_limiter = RateLimiter(rate_limit_per_minute)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "IncrementalNewsIntelligence/1.0"
        })

    def _generate_article_id(self, item: Dict[str, Any]) -> str:
        """Generate deterministic article ID from HN item."""
        item_id = item.get("id")
        url = item.get("url", "")
        
        if url:
            return hashlib.sha256(url.encode()).hexdigest()[:16]
        elif item_id:
            return hashlib.sha256(f"hn_{item_id}".encode()).hexdigest()[:16]
        else:
            logger.warning(f"HN item missing ID and URL: {item.get('title', 'Unknown')}")
            return hashlib.sha256(str(item).encode()).hexdigest()[:16]

    def _make_request(self, endpoint: str, retry_count: int = 0) -> Optional[Any]:
        """Make API request with retries and exponential backoff."""
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if retry_count < 3:
                backoff_time = 2.0 ** retry_count
                logger.warning(
                    f"HN API request failed (attempt {retry_count + 1}): {e}. "
                    f"Retrying in {backoff_time}s"
                )
                time.sleep(backoff_time)
                return self._make_request(endpoint, retry_count + 1)
            else:
                logger.error(f"HN API request failed after 3 retries: {e}")
                return None

    def _fetch_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single item by ID."""
        endpoint = f"item/{item_id}.json"
        return self._make_request(endpoint)

    def _convert_to_article(self, item: Dict[str, Any], story_type: str) -> Optional[Dict[str, Any]]:
        """
        Convert HN item to article format.
        
        Args:
            item: HN item dictionary
            story_type: Type of story list (topstories, newstories, beststories)
        
        Returns:
            Article dictionary or None if invalid
        """
        if not item:
            return None
        
        item_type = item.get("type", "")
        if item_type != "story":
            return None
        
        url = item.get("url", "")
        if not url:
            return None
        
        title = item.get("title", "")
        if not title:
            return None
        
        article_id = self._generate_article_id(item)
        
        time_stamp = item.get("time", 0)
        published_date = ""
        if time_stamp:
            try:
                dt = datetime.fromtimestamp(time_stamp)
                published_date = dt.isoformat()
            except (ValueError, OSError):
                pass
        
        author = item.get("by", "unknown")
        score = item.get("score", 0)
        descendants = item.get("descendants", 0)
        
        article = {
            "_article_id": article_id,
            "title": title,
            "url": url,
            "link": url,
            "description": item.get("text", ""),
            "snippet": title,
            "source": f"Hacker News ({author})",
            "date": published_date,
            "datePublished": published_date,
            "provider": [{"name": "Hacker News"}],
            "_ingestion_engine": f"hackernews_{story_type}",
            "_ingestion_query": story_type,
            "_hn_metadata": {
                "hn_id": item.get("id"),
                "author": author,
                "score": score,
                "comments": descendants,
                "time": time_stamp,
            }
        }
        
        return article

    def fetch_story_ids(self, story_type: str = "topstories", limit: int = 100) -> List[int]:
        """
        Fetch story IDs from HN API.
        
        Args:
            story_type: Type of stories (topstories, newstories, beststories)
            limit: Maximum number of IDs to return
        
        Returns:
            List of story IDs
        """
        endpoint = f"{story_type}.json"
        story_ids = self._make_request(endpoint)
        
        if not story_ids or not isinstance(story_ids, list):
            logger.warning(f"No story IDs returned for {story_type}")
            return []
        
        return story_ids[:limit]

    def fetch_stories(
        self,
        story_type: str = "topstories",
        max_stories: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch stories from Hacker News.
        
        Args:
            story_type: Type of stories (topstories, newstories, beststories)
            max_stories: Maximum number of stories to fetch
        
        Returns:
            List of article dictionaries
        """
        if not self.enabled:
            logger.info("Hacker News client is disabled")
            return []
        
        logger.info(f"Fetching {story_type} from Hacker News (max={max_stories})")
        
        story_ids = self.fetch_story_ids(story_type, limit=max_stories)
        
        if not story_ids:
            logger.warning(f"No story IDs found for {story_type}")
            return []
        
        articles = []
        fetched_count = 0
        
        for story_id in story_ids:
            if fetched_count >= max_stories:
                break
            
            item = self._fetch_item(story_id)
            if not item:
                continue
            
            article = self._convert_to_article(item, story_type)
            if article:
                articles.append(article)
                fetched_count += 1
            
            time.sleep(0.1)
        
        logger.info(f"Fetched {len(articles)} stories from Hacker News {story_type}")
        return articles

    def fetch_all_stories(
        self,
        max_stories_per_type: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Fetch stories from all HN lists (top, new, best).
        
        Args:
            max_stories_per_type: Maximum stories per list type
        
        Returns:
            List of all article dictionaries
        """
        all_articles = []
        
        for story_type in ["topstories", "newstories", "beststories"]:
            stories = self.fetch_stories(story_type, max_stories_per_type)
            all_articles.extend(stories)
        
        logger.info(f"Total fetched {len(all_articles)} stories from all HN lists")
        return all_articles



