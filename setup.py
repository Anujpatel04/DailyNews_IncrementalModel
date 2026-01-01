"""Setup script for incremental news intelligence system."""
from setuptools import find_packages, setup

setup(
    name="incremental-news-intelligence",
    version="1.0.0",
    description="Production-grade incremental NLP system for news intelligence",
    author="",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "sentence-transformers>=2.2.0",
        "numpy>=1.24.0",
        "flask>=3.0.0",
        "openai>=1.0.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "news-intelligence=incremental_news_intelligence.main:main",
        ],
    },
)

