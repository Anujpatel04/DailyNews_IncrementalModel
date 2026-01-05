#!/bin/bash
# Daily ingestion script
# Run this script daily to fetch new news articles

# Change to project directory
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "myenv" ]; then
    source myenv/bin/activate
fi

# Run ingestion
python3 -m incremental_news_intelligence.main ingest \
    --query "technology news" \
    --max-articles 50 \
    --freshness day

# Optional: Add more queries
# python3 -m incremental_news_intelligence.main ingest --query "artificial intelligence" --max-articles 30
# python3 -m incremental_news_intelligence.main ingest --query "climate change" --max-articles 40

echo "Daily ingestion completed at $(date)"








