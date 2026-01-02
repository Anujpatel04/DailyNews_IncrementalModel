"""Main orchestrator for incremental news intelligence system."""
import argparse
import logging
import sys
from pathlib import Path

from incremental_news_intelligence.config.settings import SystemConfig
from incremental_news_intelligence.embeddings.generator import EmbeddingGenerator
from incremental_news_intelligence.ingestion.ingester import ArticleIngester
from incremental_news_intelligence.intelligence.clustering import IncrementalClusterer
from incremental_news_intelligence.intelligence.topics import IncrementalTopicModeler
from incremental_news_intelligence.intelligence.trends import TrendDetector
from incremental_news_intelligence.processing.processor import ProcessingOrchestrator
from incremental_news_intelligence.reasoning.summarizer import (
    ClusterSummarizer,
    DailyReportGenerator,
)
from incremental_news_intelligence.storage.managers import (
    ClusterStorage,
    EmbeddingStorage,
    ProcessedArticleStorage,
    RawArticleStorage,
    TopicStorage,
    TrendStorage,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def setup_storage(config: SystemConfig) -> tuple:
    """Initialize all storage managers."""
    config.storage.base_path.mkdir(parents=True, exist_ok=True)

    raw_storage = RawArticleStorage(config.storage)
    processed_storage = ProcessedArticleStorage(config.storage)
    embedding_storage = EmbeddingStorage(config.storage)
    cluster_storage = ClusterStorage(config.storage)
    topic_storage = TopicStorage(config.storage)
    trend_storage = TrendStorage(config.storage)

    return (
        raw_storage,
        processed_storage,
        embedding_storage,
        cluster_storage,
        topic_storage,
        trend_storage,
    )

def run_ingestion_pipeline(
    config: SystemConfig,
    query: str,
    max_articles: int = 50,
    freshness: str = "day",
) -> None:
    """Run complete ingestion and processing pipeline."""
    (
        raw_storage,
        processed_storage,
        embedding_storage,
        cluster_storage,
        topic_storage,
        trend_storage,
    ) = setup_storage(config)

    logger.info("Starting ingestion pipeline")

    ingester = ArticleIngester(config.search_api, raw_storage, config.newsapi_ai, config.hackernews)
    ingested_ids = ingester.ingest_articles(
        query=query, max_articles=max_articles, freshness=freshness
    )

    logger.info(f"Ingested {len(ingested_ids)} new articles")

    processor = ProcessingOrchestrator(raw_storage, processed_storage)
    processed_ids = processor.process_new_articles()

    logger.info(f"Processed {len(processed_ids)} articles")

    embedding_generator = EmbeddingGenerator(
        config.embedding, processed_storage, embedding_storage
    )
    embedded_ids = embedding_generator.generate_new_embeddings()

    logger.info(f"Generated embeddings for {len(embedded_ids)} articles")

    clusterer = IncrementalClusterer(
        config.clustering, embedding_storage, cluster_storage, processed_storage
    )
    
    duplicates = clusterer.cleanup_duplicates()
    if duplicates:
        logger.warning(f"Found and cleaned up {len(duplicates)} duplicate article assignments")
    
    assignments = clusterer.assign_new_articles()

    logger.info(f"Assigned {len(assignments)} articles to clusters")

    topic_modeler = IncrementalTopicModeler(
        config.topic_modeling, cluster_storage, processed_storage, topic_storage
    )
    topic_modeler.update_all_cluster_topics()

    logger.info("Updated topic statistics")

    trend_detector = TrendDetector(
        config.trend_detection, cluster_storage, trend_storage
    )
    trends = trend_detector.detect_trends()

    logger.info(f"Detected trends: {trends.get('total_clusters', 0)} clusters")

    if config.llm.api_key:
        summarizer = ClusterSummarizer(
            config.llm, cluster_storage, processed_storage, topic_storage
        )
        summaries = summarizer.summarize_all_clusters()
        logger.info(f"Generated {len(summaries)} cluster summaries")
    else:
        logger.warning("LLM API key not set, skipping summarization")

def run_api_server(config: SystemConfig, port: int = 5000) -> None:
    """Run API server."""
    from incremental_news_intelligence.api.server import create_app

    (
        _,
        processed_storage,
        _,
        cluster_storage,
        _,
        trend_storage,
    ) = setup_storage(config)

    app = create_app(cluster_storage, processed_storage, trend_storage)
    logger.info(f"Starting API server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

def run_dashboard(config: SystemConfig, port: int = 5000) -> None:
    """Run dashboard web interface."""
    from incremental_news_intelligence.dashboard.app import create_dashboard_app

    app = create_dashboard_app(config)
    logger.info(f"Starting dashboard on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Incremental News Intelligence System"
    )
    parser.add_argument(
        "command",
        choices=["ingest", "api", "dashboard"],
        help="Command to run",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="technology news",
        help="Search query for ingestion",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=50,
        help="Maximum articles to ingest",
    )
    parser.add_argument(
        "--freshness",
        type=str,
        default="day",
        choices=["day", "week", "month"],
        help="Article freshness filter",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="API server port",
    )

    args = parser.parse_args()

    try:
        config = SystemConfig.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    if args.command == "ingest":
        run_ingestion_pipeline(
            config,
            query=args.query,
            max_articles=args.max_articles,
            freshness=args.freshness,
        )
    elif args.command == "api":
        run_api_server(config, port=args.port)
    elif args.command == "dashboard":
        run_dashboard(config, port=args.port)

if __name__ == "__main__":
    main()
