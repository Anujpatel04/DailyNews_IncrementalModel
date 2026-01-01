# Incremental News Intelligence System

Production-grade incremental NLP system for continuous news article ingestion, clustering, and trend detection.

## Architecture

The system is organized into strict layers with single responsibilities:

- **Ingestion**: SearchAPI Bing News client with rate limiting and retries
- **Processing**: Text normalization, deduplication, English filtering
- **Embeddings**: Incremental embedding generation using sentence transformers
- **Intelligence**: Incremental clustering, topic modeling, trend detection
- **Reasoning**: LLM-based cluster summaries and daily reports
- **API**: Read-only REST endpoints for accessing system state
- **Storage**: Persistent state management for all data types

## Requirements

- Python 3.8+
- SearchAPI key (for Bing News Search)
- OpenAI API key (optional, for summarization)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

### Option 1: Using .env file (Recommended)

Copy the example file and add your API keys:

```bash
cp .env.example .env
```

Then edit `.env` and add your API keys:

```bash
SEARCHAPI_KEY=your-searchapi-key
OPENAI_API_KEY=your-openai-api-key  # Optional
STORAGE_BASE_PATH=./data  # Optional, defaults to ./data
LOG_LEVEL=INFO  # Optional
```

### Option 2: Environment Variables

Alternatively, set environment variables directly:

```bash
export SEARCHAPI_KEY="your-searchapi-key"
export OPENAI_API_KEY="your-openai-api-key"  # Optional
export STORAGE_BASE_PATH="./data"  # Optional, defaults to ./data
export LOG_LEVEL="INFO"  # Optional
```

The system automatically loads variables from `.env` if `python-dotenv` is installed.

## Usage

### Ingest Articles

```bash
python -m incremental_news_intelligence.main ingest \
    --query "technology news" \
    --max-articles 50 \
    --freshness day
```

### Run Dashboard (Web Interface)

```bash
python -m incremental_news_intelligence.main dashboard --port 5000
```

Then open your browser to `http://localhost:5000` to access the professional web dashboard.

Features:
- **Trends View**: Visualize growing, new, and declining clusters
- **Clusters View**: Browse all topic clusters with summaries and keywords
- **Articles View**: Browse articles with cluster filtering
- **Search**: Full-text search across all articles

### Run API Server (REST API)

```bash
python -m incremental_news_intelligence.main api --port 5000
```

API endpoints:
- `GET /clusters` - List all clusters
- `GET /clusters/<cluster_id>` - Get cluster details
- `GET /trends?limit=10` - Get latest trend metrics
- `GET /articles?cluster_id=<id>&limit=50` - Get articles for cluster
- `GET /daily-summary?date=YYYY-MM-DD` - Get daily summary
- `GET /health` - Health check

## System Behavior

### Incremental Learning

- New articles are ingested and processed without retraining existing models
- Embeddings are generated only for new articles
- Clusters are updated incrementally by assigning new articles to nearest existing cluster or creating new clusters
- Topic statistics are maintained with time decay
- Trend detection compares current state to previous state

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

## Notes

- The system can run daily as a scheduled job
- Architecture supports cloud deployment without refactoring
- All embeddings are stored locally (no external vector database required)
- LLM calls are optional and only used for summarization

