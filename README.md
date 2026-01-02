# Incremental News Intelligence System

Production-grade incremental NLP system for continuous news article ingestion, clustering, and trend detection.

## Architecture

The system is organized into strict layers with single responsibilities:

- **Ingestion**: Multi-source ingestion from SearchAPI (Bing News, Google News, Google Patents), NewsAPI.ai, and Hacker News API with rate limiting and retries
- **Processing**: Text normalization, deduplication, English filtering
- **Embeddings**: Incremental embedding generation using sentence transformers
- **Intelligence**: Incremental clustering, topic modeling, trend detection
- **Reasoning**: LLM-based cluster summaries and daily reports
- **API**: Read-only REST endpoints for accessing system state
- **Storage**: Persistent state management for all data types

## Requirements

- Python 3.8+
- SearchAPI key (for Bing News, Google News, and Google Patents)
- NewsAPI.ai key (optional, for additional news sources)
- Hacker News API (free, no API key required)
- OpenAI API key (optional, for summarization)

## Installation

```bash
pip install -r requirements.txt
```

Features:
- **Trends View**: Visualize growing, new, and declining clusters
- **Clusters View**: Browse all topic clusters with summaries and keywords
- **Articles View**: Browse articles with cluster filtering
- **Search**: Full-text search across all articles

### Incremental Learning

- New articles are ingested and processed without retraining existing models
- Embeddings are generated only for new articles
- Clusters are updated incrementally by assigning new articles to the nearest existing cluster or creating new clusters
- Topic statistics are maintained with time decay
- Trend detection compares the current state to the previous state

### State Persistence

All state is persisted to disk:
- Raw articles (unchanged API responses)
- Processed articles (normalized text)
- Embeddings (vector representations)
- Cluster state (centroids, document counts, article IDs)
- Topic statistics (keyword frequencies with time decay)
- Trend metrics (growth rates, new clusters, declining clusters)

### Deterministic Processing

- Article IDs are generated deterministically from URLs
- Text normalization is deterministic
- Duplicate detection uses content hashing
- All operations are idempotent


## Design Principles

1. **Incremental**: No retraining from scratch, all updates are additive
2. **State-based**: System state persists across restarts
3. **Deterministic**: Same input produces same output
4. **Config-driven**: All thresholds and limits are configurable
5. **Layer separation**: Each layer has single responsibility
6. **No business logic in API**: API handlers only read and format data

- The system can run daily as a scheduled job
- Architecture supports cloud deployment without refactoring
- All embeddings are stored locally (no external vector database required)
- LLM calls are optional and only used for summarization

