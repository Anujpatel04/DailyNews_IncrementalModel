"""System configuration and settings."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

@dataclass
class BingNewsConfig:
    """SearchAPI Bing News configuration."""
    api_key: str
    endpoint: str = "https://www.searchapi.io/api/v1/search"
    max_results_per_query: int = 100
    rate_limit_per_minute: int = 30
    max_retries: int = 3
    retry_backoff_base: float = 2.0

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

@dataclass
class SystemConfig:
    """Main system configuration."""
    bing_news: BingNewsConfig
    embedding: EmbeddingConfig
    clustering: ClusteringConfig
    topic_modeling: TopicModelingConfig
    trend_detection: TrendDetectionConfig
    storage: StorageConfig
    llm: LLMConfig
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Load configuration from environment variables."""
        api_key = os.getenv("SEARCHAPI_KEY", "")
        if not api_key:
            raise ValueError("SEARCHAPI_KEY environment variable must be set")

        storage_base = os.getenv("STORAGE_BASE_PATH", "./data")
        storage_config = StorageConfig.from_base_path(storage_base)

        llm_api_key = os.getenv("OPENAI_API_KEY")

        return cls(
            bing_news=BingNewsConfig(api_key=api_key),
            embedding=EmbeddingConfig(),
            clustering=ClusteringConfig(),
            topic_modeling=TopicModelingConfig(),
            trend_detection=TrendDetectionConfig(),
            storage=storage_config,
            llm=LLMConfig(api_key=llm_api_key),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
