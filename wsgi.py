"""WSGI entry point for Railway deployment."""
import os
from pathlib import Path

from incremental_news_intelligence.config.settings import SystemConfig
from incremental_news_intelligence.dashboard.app import create_dashboard_app

# Load configuration
try:
    config = SystemConfig.from_env()
except ValueError as e:
    raise RuntimeError(f"Configuration error: {e}")

# Create Flask application
app = create_dashboard_app(config)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)




