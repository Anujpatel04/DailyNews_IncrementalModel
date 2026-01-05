"""MongoDB storage backend implementations."""
import logging
from typing import Any, Dict, List, Optional

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    MongoClient = None

logger = logging.getLogger(__name__)

class MongoDBStorageBackend:
    """MongoDB-based storage backend."""

    def __init__(self, connection_string: str, database_name: str, collection_name: str):
        """Initialize MongoDB storage backend."""
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo is required for MongoDB storage. Install it with: pip install pymongo")
        
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {database_name}.{collection_name}")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"MongoDB initialization error: {e}")
            raise

    def save(self, key: str, data: Any) -> None:
        """Save data with given key."""
        try:
            document = {
                "_id": key,
                "data": data,
                "updated_at": self._get_timestamp()
            }
            self.collection.replace_one(
                {"_id": key},
                document,
                upsert=True
            )
            logger.debug(f"Saved document {key} to MongoDB")
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {e}")
            raise

    def load(self, key: str) -> Optional[Any]:
        """Load data by key."""
        try:
            document = self.collection.find_one({"_id": key})
            if document:
                return document.get("data")
            return None
        except Exception as e:
            logger.error(f"Error loading from MongoDB: {e}")
            return None

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return self.collection.count_documents({"_id": key}) > 0
        except Exception as e:
            logger.error(f"Error checking existence in MongoDB: {e}")
            return False

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by prefix."""
        try:
            query = {}
            if prefix:
                query["_id"] = {"$regex": f"^{prefix}"}
            
            cursor = self.collection.find(query, {"_id": 1})
            return [doc["_id"] for doc in cursor]
        except Exception as e:
            logger.error(f"Error listing keys from MongoDB: {e}")
            return []

    def delete(self, key: str) -> bool:
        """Delete document by key."""
        try:
            result = self.collection.delete_one({"_id": key})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting from MongoDB: {e}")
            return False

    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


class MongoDBVectorStorageBackend:
    """MongoDB-based vector storage backend."""

    def __init__(self, connection_string: str, database_name: str, collection_name: str):
        """Initialize MongoDB vector storage backend."""
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo is required for MongoDB storage. Install it with: pip install pymongo")
        
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            
            # Create indexes for better performance
            self.collection.create_index("article_id", unique=True)
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB vector storage: {database_name}.{collection_name}")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"MongoDB vector storage initialization error: {e}")
            raise

    def add_embedding(
        self, article_id: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> None:
        """Add embedding for article."""
        try:
            document = {
                "article_id": article_id,
                "embedding": embedding,
                "metadata": metadata,
                "updated_at": self._get_timestamp()
            }
            self.collection.replace_one(
                {"article_id": article_id},
                document,
                upsert=True
            )
            logger.debug(f"Saved embedding for {article_id} to MongoDB")
        except Exception as e:
            logger.error(f"Error saving embedding to MongoDB: {e}")
            raise

    def get_embedding(self, article_id: str) -> Optional[List[float]]:
        """Get embedding for article."""
        try:
            document = self.collection.find_one({"article_id": article_id})
            if document:
                return document.get("embedding")
            return None
        except Exception as e:
            logger.error(f"Error loading embedding from MongoDB: {e}")
            return None

    def get_metadata(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for article."""
        try:
            document = self.collection.find_one({"article_id": article_id})
            if document:
                return document.get("metadata")
            return None
        except Exception as e:
            logger.error(f"Error loading metadata from MongoDB: {e}")
            return None

    def has_embedding(self, article_id: str) -> bool:
        """Check if embedding exists."""
        try:
            return self.collection.count_documents({"article_id": article_id}) > 0
        except Exception as e:
            logger.error(f"Error checking embedding existence in MongoDB: {e}")
            return False

    def list_article_ids(self) -> List[str]:
        """List all article IDs."""
        try:
            cursor = self.collection.find({}, {"article_id": 1})
            return [doc["article_id"] for doc in cursor]
        except Exception as e:
            logger.error(f"Error listing article IDs from MongoDB: {e}")
            return []

    def get_all_embeddings(self) -> Dict[str, List[float]]:
        """Get all embeddings."""
        try:
            cursor = self.collection.find({}, {"article_id": 1, "embedding": 1})
            return {doc["article_id"]: doc.get("embedding") for doc in cursor if doc.get("embedding")}
        except Exception as e:
            logger.error(f"Error getting all embeddings from MongoDB: {e}")
            return {}

    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get all metadata."""
        try:
            cursor = self.collection.find({}, {"article_id": 1, "metadata": 1})
            return {doc["article_id"]: doc.get("metadata", {}) for doc in cursor}
        except Exception as e:
            logger.error(f"Error getting all metadata from MongoDB: {e}")
            return {}

    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB vector storage connection closed")




