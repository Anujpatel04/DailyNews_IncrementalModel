"""Incremental clustering implementation."""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from incremental_news_intelligence.config.settings import ClusteringConfig
from incremental_news_intelligence.storage.managers import (
    ClusterStorage,
    EmbeddingStorage,
    ProcessedArticleStorage,
)

logger = logging.getLogger(__name__)

class IncrementalClusterer:
    """Incremental clustering that assigns articles to existing clusters or creates new ones."""

    def __init__(
        self,
        config: ClusteringConfig,
        embedding_storage: EmbeddingStorage,
        cluster_storage: ClusterStorage,
        processed_storage: ProcessedArticleStorage,
    ):
        """Initialize incremental clusterer."""
        self.config = config
        self.embedding_storage = embedding_storage
        self.cluster_storage = cluster_storage
        self.processed_storage = processed_storage

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def _cosine_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine distance (1 - similarity)."""
        return 1.0 - self._cosine_similarity(vec1, vec2)

    def _get_cluster_centroid(self, cluster: Dict[str, Any]) -> Optional[List[float]]:
        """Get cluster centroid embedding."""
        return cluster.get("centroid_embedding")

    def _find_article_cluster(self, article_id: str) -> Optional[str]:
        """
        Find which cluster an article currently belongs to by searching all clusters.
        
        Args:
            article_id: Article ID to search for
            
        Returns:
            Cluster ID if found, None otherwise
        """
        cluster_ids = self.cluster_storage.list_cluster_ids()
        for cluster_id in cluster_ids:
            cluster = self.cluster_storage.load_cluster(cluster_id)
            if cluster and article_id in cluster.get("article_ids", []):
                return cluster_id
        return None

    def _remove_article_from_cluster(self, cluster_id: str, article_id: str) -> None:
        """
        Remove an article from a cluster and update the cluster centroid.
        
        Args:
            cluster_id: Cluster to remove article from
            article_id: Article ID to remove
        """
        cluster = self.cluster_storage.load_cluster(cluster_id)
        if not cluster:
            return
        
        article_ids = cluster.get("article_ids", [])
        if article_id not in article_ids:
            return
        
        article_ids.remove(article_id)
        cluster["article_ids"] = article_ids
        cluster["document_count"] = max(0, cluster.get("document_count", 1) - 1)
        
        if cluster["document_count"] == 0:
            logger.warning(f"Cluster {cluster_id} has no articles after removal, but keeping it")
            cluster["centroid_embedding"] = None
        else:
            article_embedding = self.embedding_storage.get_embedding(article_id)
            if article_embedding and cluster.get("centroid_embedding"):
                current_centroid = np.array(cluster["centroid_embedding"])
                article_embedding_np = np.array(article_embedding)
                count = cluster["document_count"]
                
                if count > 0:
                    updated_centroid = (
                        (current_centroid * (count + 1) - article_embedding_np) / count
                    ).tolist()
                    cluster["centroid_embedding"] = updated_centroid
        
        cluster["last_updated"] = datetime.utcnow().isoformat()
        self.cluster_storage.save_cluster(cluster_id, cluster)
        logger.debug(f"Removed article {article_id} from cluster {cluster_id}")

    def _update_cluster_centroid(
        self, cluster_id: str, article_id: str, new_embedding: List[float]
    ) -> None:
        """
        Update cluster centroid incrementally.
        Ensures article is removed from any other cluster first.
        """
        existing_cluster_id = self._find_article_cluster(article_id)
        if existing_cluster_id and existing_cluster_id != cluster_id:
            logger.warning(
                f"Article {article_id} already in cluster {existing_cluster_id}, "
                f"removing before adding to {cluster_id}"
            )
            self._remove_article_from_cluster(existing_cluster_id, article_id)
        
        cluster = self.cluster_storage.load_cluster(cluster_id)
        if not cluster:
            return

        article_ids = cluster.get("article_ids", [])
        if article_id in article_ids:
            logger.debug(f"Article {article_id} already in cluster {cluster_id}, skipping")
            return

        current_centroid = cluster.get("centroid_embedding")
        if not current_centroid:
            cluster["centroid_embedding"] = new_embedding
        else:
            count = cluster.get("document_count", 1)
            current_centroid_np = np.array(current_centroid)
            new_embedding_np = np.array(new_embedding)

            updated_centroid = (
                (current_centroid_np * count + new_embedding_np) / (count + 1)
            ).tolist()
            cluster["centroid_embedding"] = updated_centroid

        cluster["document_count"] = cluster.get("document_count", 0) + 1
        cluster["article_ids"] = article_ids
        cluster["article_ids"].append(article_id)
        cluster["last_updated"] = datetime.utcnow().isoformat()
        self.cluster_storage.save_cluster(cluster_id, cluster)

    def _find_nearest_cluster(
        self, embedding: List[float]
    ) -> Optional[Tuple[str, float]]:
        """
        Find nearest existing cluster.

        Returns:
            Tuple of (cluster_id, distance) or None if no clusters exist
        """
        cluster_ids = self.cluster_storage.list_cluster_ids()
        if not cluster_ids:
            return None

        min_distance = float("inf")
        nearest_cluster_id = None

        for cluster_id in cluster_ids:
            cluster = self.cluster_storage.load_cluster(cluster_id)
            if not cluster:
                continue

            centroid = self._get_cluster_centroid(cluster)
            if not centroid:
                continue

            distance = self._cosine_distance(embedding, centroid)
            if distance < min_distance:
                min_distance = distance
                nearest_cluster_id = cluster_id

        if nearest_cluster_id is None:
            return None

        return (nearest_cluster_id, min_distance)

    def _create_new_cluster(self, article_id: str, embedding: List[float]) -> str:
        """
        Create new cluster with single article.
        Ensures article is removed from any existing cluster first.
        """
        existing_cluster_id = self._find_article_cluster(article_id)
        if existing_cluster_id:
            logger.warning(
                f"Article {article_id} already in cluster {existing_cluster_id}, "
                f"removing before creating new cluster"
            )
            self._remove_article_from_cluster(existing_cluster_id, article_id)
        
        cluster_id = f"cluster_{uuid.uuid4().hex[:8]}"
        cluster = {
            "cluster_id": cluster_id,
            "centroid_embedding": embedding,
            "document_count": 1,
            "article_ids": [article_id],
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
        }
        self.cluster_storage.save_cluster(cluster_id, cluster)
        logger.info(f"Created new cluster {cluster_id}")
        return cluster_id

    def assign_article(self, article_id: str) -> Optional[str]:
        """
        Assign article to existing cluster or create new one.
        Ensures article is only in one cluster at a time.

        Args:
            article_id: Article ID

        Returns:
            Cluster ID that article was assigned to
        """
        embedding = self.embedding_storage.get_embedding(article_id)
        if not embedding:
            logger.warning(f"No embedding found for {article_id}")
            return None

        existing_cluster_id = self._find_article_cluster(article_id)
        metadata = self.embedding_storage.get_metadata(article_id)
        metadata_cluster_id = metadata.get("cluster_id") if metadata else None
        
        if existing_cluster_id and metadata_cluster_id and existing_cluster_id == metadata_cluster_id:
            logger.debug(f"Article {article_id} already correctly assigned to cluster {existing_cluster_id}")
            return existing_cluster_id
        
        if existing_cluster_id and existing_cluster_id != metadata_cluster_id:
            logger.warning(
                f"Article {article_id} found in cluster {existing_cluster_id} but metadata says {metadata_cluster_id}, "
                f"removing from {existing_cluster_id}"
            )
            self._remove_article_from_cluster(existing_cluster_id, article_id)

        nearest = self._find_nearest_cluster(embedding)
        if nearest is None:
            cluster_id = self._create_new_cluster(article_id, embedding)
        else:
            cluster_id, distance = nearest
            if distance <= self.config.distance_threshold:
                self._update_cluster_centroid(cluster_id, article_id, embedding)
                logger.debug(
                    f"Assigned {article_id} to existing cluster {cluster_id} "
                    f"(distance={distance:.3f})"
                )
            else:
                cluster_id = self._create_new_cluster(article_id, embedding)
                logger.debug(
                    f"Created new cluster {cluster_id} for {article_id} "
                    f"(distance={distance:.3f} > threshold={self.config.distance_threshold})"
                )

        metadata = self.embedding_storage.get_metadata(article_id) or {}
        metadata["cluster_id"] = cluster_id
        self.embedding_storage.save_embedding(article_id, embedding, metadata)

        return cluster_id

    def assign_new_articles(self) -> Dict[str, str]:
        """
        Assign all unassigned articles to clusters.
        Also ensures no articles are duplicated across clusters.

        Returns:
            Dictionary mapping article_id to cluster_id
        """
        all_embeddings = self.embedding_storage.get_all_embeddings()
        assignments = {}

        for article_id, embedding in all_embeddings.items():
            existing_cluster_id = self._find_article_cluster(article_id)
            metadata = self.embedding_storage.get_metadata(article_id)
            metadata_cluster_id = metadata.get("cluster_id") if metadata else None
            
            if existing_cluster_id and metadata_cluster_id:
                if existing_cluster_id == metadata_cluster_id:
                    continue
                else:
                    logger.warning(
                        f"Article {article_id} has inconsistent cluster assignment: "
                        f"found in {existing_cluster_id}, metadata says {metadata_cluster_id}. "
                        f"Reassigning to ensure consistency."
                    )
                    self._remove_article_from_cluster(existing_cluster_id, article_id)

            cluster_id = self.assign_article(article_id)
            if cluster_id:
                assignments[article_id] = cluster_id

        logger.info(f"Assigned {len(assignments)} articles to clusters")
        return assignments

    def cleanup_duplicates(self) -> Dict[str, List[str]]:
        """
        Find and remove duplicate article assignments across clusters.
        
        Returns:
            Dictionary mapping article_id to list of cluster_ids it was found in
        """
        duplicates = {}
        cluster_ids = self.cluster_storage.list_cluster_ids()
        
        article_to_clusters = {}
        for cluster_id in cluster_ids:
            cluster = self.cluster_storage.load_cluster(cluster_id)
            if not cluster:
                continue
            
            for article_id in cluster.get("article_ids", []):
                if article_id not in article_to_clusters:
                    article_to_clusters[article_id] = []
                article_to_clusters[article_id].append(cluster_id)
        
        for article_id, cluster_list in article_to_clusters.items():
            if len(cluster_list) > 1:
                duplicates[article_id] = cluster_list
                logger.warning(
                    f"Article {article_id} found in {len(cluster_list)} clusters: {cluster_list}. "
                    f"Keeping only in {cluster_list[0]}, removing from others."
                )
                for cluster_id in cluster_list[1:]:
                    self._remove_article_from_cluster(cluster_id, article_id)
        
        if duplicates:
            logger.info(f"Cleaned up {len(duplicates)} duplicate article assignments")
        else:
            logger.info("No duplicate article assignments found")
        
        return duplicates
