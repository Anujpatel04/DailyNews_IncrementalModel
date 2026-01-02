"""System configuration and settings."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

@dataclass
class SearchAPIConfig:
    """SearchAPI configuration for multiple engines."""
    api_key: str
    endpoint: str = "https://www.searchapi.io/api/v1/search"
    max_results_per_query: int = 100
    rate_limit_per_minute: int = 30
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    enabled_engines: List[str] = None

    def __post_init__(self):
        if self.enabled_engines is None:
            self.enabled_engines = ["bing_news", "google_news", "google_patents"]

@dataclass
class NewsAPIAIConfig:
    """NewsAPI.ai configuration."""
    api_key: str
    endpoint: str = "https://newsapi.ai/api/v1/search"
    max_results_per_query: int = 100
    rate_limit_per_minute: int = 30
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    enabled: bool = True

@dataclass
class HackerNewsConfig:
    """Hacker News API configuration."""
    enabled: bool = True
    rate_limit_per_minute: int = 60
    max_stories_per_type: int = 30
    fetch_types: List[str] = None

    def __post_init__(self):
        if self.fetch_types is None:
            self.fetch_types = ["topstories", "newstories", "beststories"]

@dataclass
class EmbeddingConfig:
    """Embedding generation configuration."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 32
    device: str = "cpu"

@dataclass
class ClusteringConfig:
    """Incremental clustering configuration."""
    distance_threshold: float = 0.5
    min_cluster_size: int = 2
    similarity_metric: str = "cosine"

@dataclass
class TopicModelingConfig:
    """Topic modeling configuration."""
    time_decay_factor: float = 0.95
    min_keyword_frequency: int = 2
    top_keywords_per_cluster: int = 10

@dataclass
class TrendDetectionConfig:
    """Trend detection configuration."""
    growth_threshold: float = 1.5
    new_cluster_window_hours: int = 24
    decline_threshold: float = 0.5

@dataclass
class StorageConfig:
    """Storage configuration."""
    base_path: Path
    raw_articles_dir: Path
    processed_articles_dir: Path
    embeddings_dir: Path
    clusters_dir: Path
    topics_dir: Path
    trends_dir: Path

    @classmethod
    def from_base_path(cls, base_path: str) -> "StorageConfig":
        """Create storage config from base path."""
        base = Path(base_path)
        return cls(
            base_path=base,
            raw_articles_dir=base / "raw_articles",
            processed_articles_dir=base / "processed_articles",
            embeddings_dir=base / "embeddings",
            clusters_dir=base / "clusters",
            topics_dir=base / "topics",
            trends_dir=base / "trends",
        )

@dataclass
class LLMConfig:
    """LLM configuration for reasoning layer."""
    provider: str = "openai"
    model_name: str = "gpt-4"
    api_key: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 1000
    azure_endpoint: Optional[str] = None
    api_version: Optional[str] = None

@dataclass
class SystemConfig:
    """Main system configuration."""
    search_api: SearchAPIConfig
    embedding: EmbeddingConfig
    clustering: ClusteringConfig
    topic_modeling: TopicModelingConfig
    trend_detection: TrendDetectionConfig
    storage: StorageConfig
    llm: LLMConfig
    newsapi_ai: Optional[NewsAPIAIConfig] = None
    hackernews: Optional[HackerNewsConfig] = None
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Load configuration from environment variables."""
        api_key = os.getenv("SEARCHAPI_KEY", "")
        if not api_key:
            raise ValueError("SEARCHAPI_KEY environment variable must be set")

        storage_base = os.getenv("STORAGE_BASE_PATH", "./data")
        storage_config = StorageConfig.from_base_path(storage_base)

        llm_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        
        if azure_endpoint:
            provider = "azure"
            model_name = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")
            if "deployments/" in azure_endpoint:
                deployment_match = azure_endpoint.split("deployments/")[1].split("/")[0]
                if deployment_match:
                    model_name = deployment_match
        else:
            provider = os.getenv("LLM_PROVIDER", "openai")
            model_name = os.getenv("OPENAI_MODEL", "gpt-4")

        enabled_engines_str = os.getenv("SEARCHAPI_ENGINES", "bing_news,google_news,google_patents")
        enabled_engines = [e.strip() for e in enabled_engines_str.split(",") if e.strip()]

        newsapi_ai_key = os.getenv("NEWSAPI_AI_KEY", "")
        newsapi_ai_config = None
        if newsapi_ai_key:
            newsapi_ai_enabled = os.getenv("NEWSAPI_AI_ENABLED", "true").lower() == "true"
            newsapi_ai_config = NewsAPIAIConfig(api_key=newsapi_ai_key, enabled=newsapi_ai_enabled)

        hackernews_enabled = os.getenv("HACKERNEWS_ENABLED", "true").lower() == "true"
        hackernews_max_stories = int(os.getenv("HACKERNEWS_MAX_STORIES", "30"))
        hackernews_types_str = os.getenv("HACKERNEWS_TYPES", "topstories,newstories,beststories")
        hackernews_types = [t.strip() for t in hackernews_types_str.split(",") if t.strip()]
        hackernews_config = HackerNewsConfig(
            enabled=hackernews_enabled,
            max_stories_per_type=hackernews_max_stories,
            fetch_types=hackernews_types
        )

        llm_config = LLMConfig(
            provider=provider,
            model_name=model_name,
            api_key=llm_api_key,
            azure_endpoint=azure_endpoint if azure_endpoint else None,
            api_version=azure_api_version if azure_endpoint else None,
        )

        return cls(
            search_api=SearchAPIConfig(api_key=api_key, enabled_engines=enabled_engines),
            newsapi_ai=newsapi_ai_config,
            hackernews=hackernews_config,
            embedding=EmbeddingConfig(),
            clustering=ClusteringConfig(),
            topic_modeling=TopicModelingConfig(),
            trend_detection=TrendDetectionConfig(),
            storage=storage_config,
            llm=llm_config,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
