"""Vector Store - Manage document embeddings in vector database"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result with score"""

    chunk_id: str
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class VectorStore:
    """Vector database interface for storing and retrieving embeddings"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize vector store

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self._client = None
        self._collection = None

        # Get vector DB settings
        vector_db_config = self.config.get("vector_db", self.config)
        self.provider = vector_db_config.get("provider", "milvus")
        self.host = vector_db_config.get("host", "localhost")
        self.port = vector_db_config.get("port", 19530)
        self.collection_name = vector_db_config.get("collection", "knowledge_base")
        self.dimension = vector_db_config.get("dimension", 1024)

        # Index settings
        self.index_type = vector_db_config.get("index_type", "HNSW")
        self.metric_type = vector_db_config.get("metric_type", "COSINE")

    def _get_client(self):
        """Get or create vector database client

        Returns:
            Database client
        """
        if self._client is not None:
            return self._client

        if self.provider == "milvus":
            try:
                from pymilvus import MilvusClient

                self._client = MilvusClient(
                    uri=f"http://{self.host}:{self.port}",
                )
                logger.info(f"Connected to Milvus at {self.host}:{self.port}")
            except ImportError:
                logger.error("pymilvus not installed. Run: pip install pymilvus")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Milvus: {e}")
                raise
        else:
            raise ValueError(f"Unsupported vector DB provider: {self.provider}")

        return self._client

    def create_collection(self, collection_name: Optional[str] = None) -> bool:
        """Create a collection for storing embeddings

        Args:
            collection_name: Name of collection (default from config)

        Returns:
            True if successful
        """
        client = self._get_client()
        name = collection_name or self.collection_name

        try:
            if self.provider == "milvus":
                # Check if collection exists
                if client.has_collection(name):
                    logger.info(f"Collection '{name}' already exists")
                    return True

                # Create collection
                client.create_collection(
                    collection_name=name,
                    dimension=self.dimension,
                )

                logger.info(f"Created collection '{name}' with dimension {self.dimension}")
                return True
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False

    def insert(
        self,
        chunks: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
    ) -> int:
        """Insert chunk embeddings into the store

        Args:
            chunks: List of chunk dicts with chunk_id, content, embedding, metadata
            collection_name: Name of collection

        Returns:
            Number of chunks inserted
        """
        client = self._get_client()
        name = collection_name or self.collection_name

        if not chunks:
            return 0

        try:
            if self.provider == "milvus":
                # Prepare data
                data = []
                for chunk in chunks:
                    data.append(
                        {
                            "id": chunk.get("chunk_id", f"chunk_{chunk.get('index', 0)}"),
                            "vector": chunk["embedding"],
                            "text": chunk.get("content", ""),
                            # Store metadata as JSON string
                            "metadata": chunk.get("metadata", {}),
                        }
                    )

                # Insert
                client.insert(collection_name=name, data=data)
                logger.info(f"Inserted {len(data)} chunks into collection '{name}'")
                return len(data)
        except Exception as e:
            logger.error(f"Failed to insert chunks: {e}")
            return 0

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: Optional[str] = None,
    ) -> List[SearchResult]:
        """Search for similar chunks

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            collection_name: Name of collection

        Returns:
            List of search results
        """
        client = self._get_client()
        name = collection_name or self.collection_name

        try:
            if self.provider == "milvus":
                results = client.search(
                    collection_name=name,
                    data=[query_embedding],
                    limit=top_k,
                    output_fields=["text", "metadata"],
                )

                search_results = []
                for hit in results[0]:  # First query's results
                    search_results.append(
                        SearchResult(
                            chunk_id=hit.get("id", ""),
                            content=hit.get("text", ""),
                            score=hit.get("distance", 0.0),
                            metadata=hit.get("metadata"),
                        )
                    )

                return search_results
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return []

    def delete(
        self,
        chunk_ids: List[str],
        collection_name: Optional[str] = None,
    ) -> int:
        """Delete chunks by IDs

        Args:
            chunk_ids: List of chunk IDs to delete
            collection_name: Name of collection

        Returns:
            Number of chunks deleted
        """
        client = self._get_client()
        name = collection_name or self.collection_name

        try:
            if self.provider == "milvus":
                client.delete(collection_name=name, ids=chunk_ids)
                logger.info(f"Deleted {len(chunk_ids)} chunks from collection '{name}'")
                return len(chunk_ids)
        except Exception as e:
            logger.error(f"Failed to delete chunks: {e}")
            return 0

    def drop_collection(self, collection_name: Optional[str] = None) -> bool:
        """Drop a collection

        Args:
            collection_name: Name of collection

        Returns:
            True if successful
        """
        client = self._get_client()
        name = collection_name or self.collection_name

        try:
            if self.provider == "milvus":
                client.drop_collection(collection_name=name)
                logger.info(f"Dropped collection '{name}'")
                return True
        except Exception as e:
            logger.error(f"Failed to drop collection: {e}")
            return False

    def count(self, collection_name: Optional[str] = None) -> int:
        """Count documents in collection

        Args:
            collection_name: Name of collection

        Returns:
            Number of documents
        """
        client = self._get_client()
        name = collection_name or self.collection_name

        try:
            if self.provider == "milvus":
                # For Milvus lite client, we need to query stats
                stats = client.get_collection_stats(collection_name=name)
                return stats.get("row_count", 0)
        except Exception as e:
            logger.error(f"Failed to get collection count: {e}")
            return 0
