# database/qdrant_manager.py
import os
import logging
import hashlib
import json
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)

class QdrantManager:
    def __init__(self):
        self.client = QdrantClient(
            url=os.getenv('QDRANT_URL'),
            api_key=os.getenv('QDRANT_API_KEY')
        )
        self.vector_size = 1536  # OpenAI embedding size

    def _normalize_content(self, content: Any) -> str:
        """
        Ensure the content is a string before embedding.
        Handles CrewOutput, TaskOutput, dict, list, etc.
        """
        try:
            # If it's already a string
            if isinstance(content, str):
                return content.strip()

            # CrewOutput or TaskOutput style objects
            if hasattr(content, "raw"):
                return str(content.raw).strip()
            if hasattr(content, "summary") and content.summary:
                return str(content.summary).strip()

            # Dict or list — convert to JSON
            if isinstance(content, (dict, list)):
                return json.dumps(content, ensure_ascii=False)

            # Fallback — convert to string
            return str(content).strip()

        except Exception as e:
            logger.error(f"Error normalizing content: {e}")
            return ""

    async def create_project_collection(self, project_id: str):
        """Create a collection for project-specific embeddings"""
        try:
            collection_name = f"project_{project_id}"
            collections = self.client.get_collections()

            if collection_name not in [c.name for c in collections.collections]:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error creating collection: {e}")

    async def add_content_embedding(self, project_id: str, content: Any, metadata: Dict, embedding: List[float]):
        """Add content embedding to project collection"""
        try:
            normalized_content = self._normalize_content(content)
            if not normalized_content:
                logger.warning(f"Skipping empty content for project {project_id}")
                return

            collection_name = f"project_{project_id}"
            content_hash = hashlib.md5(normalized_content.encode("utf-8")).hexdigest()

            point = PointStruct(
                id=content_hash,
                vector=embedding,
                payload={
                    "content": normalized_content,
                    "metadata": metadata,
                    "timestamp": metadata.get('created_at', ''),
                    "platform": metadata.get('platform', ''),
                    "content_type": metadata.get('content_type', '')
                }
            )

            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            logger.info(f"Added embedding for project {project_id} (hash={content_hash})")

        except Exception as e:
            logger.error(f"Error adding embedding: {e}")

    async def search_similar_content(self, project_id: str, query_embedding: List[float], limit: int = 5) -> List[Dict]:
        """Search for similar content in project collection"""
        try:
            collection_name = f"project_{project_id}"
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True
            )

            return [
                {
                    "content": scored_point.payload.get("content", ""),
                    "score": scored_point.score,
                    "metadata": scored_point.payload.get("metadata", {})
                }
                for scored_point in search_result
            ]

        except Exception as e:
            logger.error(f"Error searching similar content: {e}")
            return []

    async def get_project_analytics(self, project_id: str) -> Dict:
        """Get analytics for project content"""
        try:
            collection_name = f"project_{project_id}"
            collection_info = self.client.get_collection(collection_name)

            platforms = {}
            scroll_result = self.client.scroll(
                collection_name=collection_name,
                with_payload=True,
                limit=1000
            )

            for point in scroll_result[0]:
                platform = point.payload.get("platform", "unknown")
                platforms[platform] = platforms.get(platform, 0) + 1

            return {
                "total_content": collection_info.points_count,
                "platforms": platforms,
                "vector_size": collection_info.config.params.vectors.size
            }

        except Exception as e:
            logger.error(f"Error getting project analytics: {e}")
            return {}

    async def delete_project_collection(self, project_id: str):
        """Delete project collection"""
        try:
            collection_name = f"project_{project_id}"
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
