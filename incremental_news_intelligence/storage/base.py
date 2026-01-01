"""Base storage interfaces and implementations."""
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def save(self, key: str, data: Any) -> None:
        """Save data with given key."""
        pass

    @abstractmethod
    def load(self, key: str) -> Optional[Any]:
        """Load data by key."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by prefix."""
        pass

class FileStorageBackend(StorageBackend):
    """File-based storage backend."""

    def __init__(self, base_path: Path):
        """Initialize file storage backend."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized file storage at {self.base_path}")

    def _get_path(self, key: str) -> Path:
        """Get file path for key."""
        return self.base_path / f"{key}.json"

    def save(self, key: str, data: Any) -> None:
        """Save data to JSON file."""
        file_path = self._get_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved data to {file_path}")

    def load(self, key: str) -> Optional[Any]:
        """Load data from JSON file."""
        file_path = self._get_path(key)
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading {file_path}: {e}")
            return None

    def exists(self, key: str) -> bool:
        """Check if file exists."""
        return self._get_path(key).exists()

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all JSON files, optionally filtered by prefix."""
        pattern = f"{prefix}*.json" if prefix else "*.json"
        files = list(self.base_path.glob(pattern))
        return [f.stem for f in files]

class VectorStorageBackend:
    """Simple in-memory vector storage with file persistence."""

    def __init__(self, base_path: Path):
        """Initialize vector storage."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._vectors: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._load_state()

    def _get_vectors_path(self) -> Path:
        """Get path for vectors file."""
        return self.base_path / "vectors.json"

    def _get_metadata_path(self) -> Path:
        """Get path for metadata file."""
        return self.base_path / "metadata.json"

    def _load_state(self) -> None:
        """Load vectors and metadata from disk."""
        vectors_path = self._get_vectors_path()
        metadata_path = self._get_metadata_path()

        if vectors_path.exists():
            with open(vectors_path, "r", encoding="utf-8") as f:
                self._vectors = json.load(f)

        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)

        logger.info(f"Loaded {len(self._vectors)} vectors from storage")

    def _save_state(self) -> None:
        """Save vectors and metadata to disk."""
        vectors_path = self._get_vectors_path()
        metadata_path = self._get_metadata_path()

        with open(vectors_path, "w", encoding="utf-8") as f:
            json.dump(self._vectors, f, indent=2)

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved {len(self._vectors)} vectors to storage")

    def add_embedding(
        self, article_id: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> None:
        """Add embedding for article."""
        if article_id in self._vectors:
            logger.warning(f"Overwriting existing embedding for {article_id}")
        self._vectors[article_id] = embedding
        self._metadata[article_id] = metadata
        self._save_state()

    def get_embedding(self, article_id: str) -> Optional[List[float]]:
        """Get embedding for article."""
        return self._vectors.get(article_id)

    def get_metadata(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for article."""
        return self._metadata.get(article_id)

    def has_embedding(self, article_id: str) -> bool:
        """Check if embedding exists."""
        return article_id in self._vectors

    def list_article_ids(self) -> List[str]:
        """List all article IDs."""
        return list(self._vectors.keys())

    def get_all_embeddings(self) -> Dict[str, List[float]]:
        """Get all embeddings."""
        return self._vectors.copy()

    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get all metadata."""
        return self._metadata.copy()
