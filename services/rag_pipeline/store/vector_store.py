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
        elif self.provider == "qdrant":
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import Distance, VectorParams, PointStruct

                self._client = QdrantClient(url=f"http://{self.host}:{self.port}")
                self._qdrant_models = {"Distance": Distance, "VectorParams": VectorParams, "PointStruct": PointStruct}
                logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
            except ImportError:
                logger.error("qdrant-client not installed. Run: pip install qdrant-client")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Qdrant: {e}")
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
            elif self.provider == "qdrant":
                from qdrant_client.models import Distance, VectorParams

                # Check if collection exists
                collections = client.get_collections().collections
                collection_names = [c.name for c in collections]
                if name in collection_names:
                    logger.info(f"Collection '{name}' already exists")
                    return True

                # Create collection
                client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
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
            elif self.provider == "qdrant":
                from qdrant_client.models import PointStruct
                import uuid

                # Prepare points - Qdrant requires integer or UUID for id
                points = []
                for idx, chunk in enumerate(chunks):
                    chunk_id = chunk.get("chunk_id", "")
                    # Use hash of chunk_id to generate consistent integer ID, or use index
                    if chunk_id:
                        point_id = abs(hash(chunk_id)) % (2 ** 63)  # Convert to positive 64-bit integer
                    else:
                        point_id = idx

                    point = PointStruct(
                        id=point_id,
                        vector=chunk["embedding"],
                        payload={
                            "text": chunk.get("content", ""),
                            "metadata": chunk.get("metadata", {}),
                            "chunk_id": chunk_id,  # Store original chunk_id in payload
                        },
                    )
                    points.append(point)

                # Insert
                client.upsert(collection_name=name, points=points)
                logger.info(f"Inserted {len(points)} chunks into collection '{name}'")
                return len(points)
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
            elif self.provider == "qdrant":
                from qdrant_client.models import NearestQuery

                results = client.query_points(
                    collection_name=name,
                    query=NearestQuery(nearest=query_embedding),
                    limit=top_k,
                )

                search_results = []
                for hit in results.points:
                    search_results.append(
                        SearchResult(
                            chunk_id=hit.payload.get("chunk_id", str(hit.id)),
                            content=hit.payload.get("text", ""),
                            score=hit.score,
                            metadata=hit.payload.get("metadata"),
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
            elif self.provider == "qdrant":
                client.delete(collection_name=name, points_selector=chunk_ids)
                logger.info(f"Deleted {len(chunk_ids)} chunks from collection '{name}'")
                return len(chunk_ids)
        except Exception as e:
            logger.error(f"Failed to delete chunks: {e}")
            return 0

    def delete_by_doc_id(
        self,
        doc_id: str,
        collection_name: Optional[str] = None,
    ) -> bool:
        """Delete all chunks belonging to a document

        Args:
            doc_id: Document ID
            collection_name: Name of collection

        Returns:
            True if successful
        """
        client = self._get_client()
        name = collection_name or self.collection_name

        try:
            if self.provider == "milvus":
                # Assuming dynamic schema or JSON field for metadata
                # Expression for JSON field query
                filter_expr = f'metadata["doc_id"] == "{doc_id}"'
                client.delete(collection_name=name, filter=filter_expr)
                logger.info(f"Deleted documents with doc_id '{doc_id}' from collection '{name}'")
                return True
            elif self.provider == "qdrant":
                from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector

                client.delete(
                    collection_name=name,
                    points_selector=FilterSelector(
                        filter=Filter(
                            must=[
                                FieldCondition(
                                    key="metadata.doc_id",
                                    match=MatchValue(value=doc_id),
                                )
                            ]
                        )
                    ),
                )
                logger.info(f"Deleted documents with doc_id '{doc_id}' from collection '{name}'")
                return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

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
            elif self.provider == "qdrant":
                client.delete_collection(collection_name=name)
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
            elif self.provider == "qdrant":
                collection_info = client.get_collection(name)
                return collection_info.points_count
        except Exception as e:
            logger.error(f"Failed to get collection count: {e}")
            return 0

    def fetch_all_chunks(
        self,
        collection_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        client = self._get_client()
        name = collection_name or self.collection_name

        try:
            if self.provider == "qdrant":
                chunks = []
                offset = None
                page_limit = 256
                remaining = limit

                while True:
                    current_limit = page_limit
                    if remaining is not None:
                        current_limit = min(current_limit, remaining)

                    points, next_offset = client.scroll(
                        collection_name=name,
                        limit=current_limit,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False,
                    )

                    for point in points:
                        payload = point.payload or {}
                        chunks.append(
                            {
                                "chunk_id": payload.get("chunk_id", str(point.id)),
                                "content": payload.get("text", ""),
                                "metadata": payload.get("metadata", {}),
                            }
                        )

                    if remaining is not None:
                        remaining -= len(points)
                        if remaining <= 0:
                            break

                    if not next_offset or not points:
                        break

                    offset = next_offset

                return chunks
            elif self.provider == "milvus":
                return []
        except Exception as e:
            logger.error(f"Failed to fetch chunks: {e}")
            return []
