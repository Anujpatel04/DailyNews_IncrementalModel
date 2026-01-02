"""Text normalization and preprocessing."""
import hashlib
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class TextNormalizer:
    """Deterministic text normalization."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text deterministically.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        if not text:
            return ""

        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    @staticmethod
    def extract_full_text(article: Dict[str, Any]) -> str:
        """
        Extract full text from article.

        Args:
            article: Raw article dictionary

        Returns:
            Combined text content
        """
        parts = []

        title = article.get("title") or article.get("name", "")
        if title:
            parts.append(title)

        snippet = article.get("snippet", "")
        if snippet:
            parts.append(snippet)

        description = article.get("description", "")
        if description:
            parts.append(description)

        body = article.get("body", "")
        if body:
            parts.append(body)

        return " ".join(parts)

    @staticmethod
    def is_english(text: str) -> bool:
        """
        Simple English language detection.

        Args:
            text: Text to check

        Returns:
            True if likely English
        """
        if not text:
            return False

        ascii_ratio = sum(1 for c in text if ord(c) < 128) / len(text)
        return ascii_ratio > 0.85

class DuplicateDetector:
    """Detect duplicate articles using content hashing."""

    @staticmethod
    def compute_content_hash(text: str) -> str:
        """
        Compute deterministic hash of text content.

        Args:
            text: Text content

        Returns:
            SHA256 hash (hex)
        """
        normalized = TextNormalizer.normalize_text(text)
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def compute_similarity(text1: str, text2: str) -> float:
        """
        Compute simple similarity ratio between texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity ratio [0, 1]
        """
        words1 = set(TextNormalizer.normalize_text(text1).lower().split())
        words2 = set(TextNormalizer.normalize_text(text2).lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

class ArticleProcessor:
    """Process raw articles into normalized format."""

    def __init__(self, similarity_threshold: float = 0.9):
        """Initialize processor."""
        self.similarity_threshold = similarity_threshold
        self.normalizer = TextNormalizer()
        self.duplicate_detector = DuplicateDetector()

    def process_article(
        self, raw_article: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process raw article into standardized format.

        Args:
            raw_article: Raw article from API

        Returns:
            Processed article or None if filtered out
        """
        article_id = raw_article.get("_article_id")
        if not article_id:
            logger.warning("Article missing ID")
            return None

        full_text = self.normalizer.extract_full_text(raw_article)
        normalized_text = self.normalizer.normalize_text(full_text)

        if not normalized_text or len(normalized_text) < 50:
            logger.debug(f"Article {article_id} too short, filtering")
            return None

        if not self.normalizer.is_english(normalized_text):
            logger.debug(f"Article {article_id} not English, filtering")
            return None

        content_hash = self.duplicate_detector.compute_content_hash(normalized_text)

        title = raw_article.get("title") or raw_article.get("name", "")
        url = raw_article.get("link") or raw_article.get("url", "")
        source = raw_article.get("source", "")
        if not source:
            provider = raw_article.get("provider", [])
            if provider and isinstance(provider, list) and len(provider) > 0:
                source = provider[0].get("name", "unknown") if isinstance(provider[0], dict) else "unknown"
            else:
                source = "unknown"
        published_date = raw_article.get("date") or raw_article.get("datePublished", "")

        engine = raw_article.get("_ingestion_engine", "unknown")
        
        processed = {
            "article_id": article_id,
            "title": title,
            "description": raw_article.get("snippet") or raw_article.get("description", ""),
            "text": normalized_text,
            "url": url,
            "source": source,
            "published_date": published_date,
            "content_hash": content_hash,
            "word_count": len(normalized_text.split()),
            "char_count": len(normalized_text),
            "ingestion_engine": engine,
        }

        return processed
