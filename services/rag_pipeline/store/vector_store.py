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
        self.collection_name = vector_db_config.get("collection", "knowledge_bases")
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

                # Create schema for Multi-KB support
                from pymilvus import DataType
                
                schema = client.create_schema(
                    auto_id=True,
                    enable_dynamic_field=True,
                )
                
                # Primary Key
                schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
                
                # Vector
                schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self.dimension)
                
                # Partition Key (KB ID)
                schema.add_field(field_name="kb_id", datatype=DataType.VARCHAR, max_length=64, is_partition_key=True)
                
                # Metadata fields (explicitly defined for better performance, though dynamic is enabled)
                schema.add_field(field_name="doc_id", datatype=DataType.VARCHAR, max_length=64)
                schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)

                # Index params
                index_params = client.prepare_index_params()
                index_params.add_index(
                    field_name="vector",
                    index_type=self.index_type,
                    metric_type=self.metric_type,
                    params={"M": 16, "efConstruction": 256}
                )

                # Create collection
                client.create_collection(
                    collection_name=name,
                    schema=schema,
                    index_params=index_params
                )

                logger.info(f"Created collection '{name}' with dimension {self.dimension} and partition key 'kb_id'")
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
        kb_id: str = "default"
    ) -> int:
        """Insert chunk embeddings into the store

        Args:
            chunks: List of chunk dicts with chunk_id, content, embedding, metadata
            collection_name: Name of collection
            kb_id: Knowledge Base ID

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
                    metadata = chunk.get("metadata", {})
                    doc_id = metadata.get("doc_id", "")
                    
                    data.append(
                        {
                            "vector": chunk["embedding"],
                            "text": chunk.get("content", ""),
                            "kb_id": kb_id,
                            "doc_id": doc_id,
                            "chunk_id": chunk.get("chunk_id", ""), # Stored in dynamic field
                            "metadata": metadata, # Stored in dynamic field
                        }
                    )

                # Insert
                client.insert(collection_name=name, data=data)
                logger.info(f"Inserted {len(data)} chunks into collection '{name}' (kb_id={kb_id})")
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
                            "chunk_id": chunk_id,
                            "kb_id": kb_id, # Store kb_id in payload for filtering
                            "doc_id": chunk.get("metadata", {}).get("doc_id", "")
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
        kb_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Search for similar chunks

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            collection_name: Name of collection
            kb_ids: List of Knowledge Base IDs to filter by

        Returns:
            List of search results
        """
        client = self._get_client()
        name = collection_name or self.collection_name

        try:
            if self.provider == "milvus":
                # Construct filter expression for kb_ids
                filter_expr = None
                if kb_ids:
                    # Milvus 'in' operator syntax: kb_id in ["id1", "id2"]
                    ids_str = ", ".join([f'"{kid}"' for kid in kb_ids])
                    filter_expr = f'kb_id in [{ids_str}]'

                results = client.search(
                    collection_name=name,
                    data=[query_embedding],
                    limit=top_k,
                    filter=filter_expr,
                    output_fields=["text", "metadata", "chunk_id", "kb_id", "doc_id"],
                )

                search_results = []
                for hit in results[0]:  # First query's results
                    # Milvus returns entity fields in hit['entity'] or directly in hit depending on client version
                    # PyMilvus High Level Client returns dict-like object
                    
                    search_results.append(
                        SearchResult(
                            chunk_id=hit.get("chunk_id", str(hit.get("id"))),
                            content=hit.get("text", ""),
                            score=hit.get("distance", 0.0),
                            metadata=hit.get("metadata"),
                        )
                    )

                return search_results
            elif self.provider == "qdrant":
                from qdrant_client.models import NearestQuery, Filter, FieldCondition, MatchValue, MatchAny

                query_filter = None
                if kb_ids:
                    if len(kb_ids) == 1:
                        query_filter = Filter(
                            must=[
                                FieldCondition(
                                    key="kb_id",
                                    match=MatchValue(value=kb_ids[0])
                                )
                            ]
                        )
                    else:
                        query_filter = Filter(
                            must=[
                                FieldCondition(
                                    key="kb_id",
                                    match=MatchAny(any=kb_ids)
                                )
                            ]
                        )

                results = client.query_points(
                    collection_name=name,
                    query=NearestQuery(nearest=query_embedding, filter=query_filter),
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
        
        Note: With auto_id=True in Milvus, we usually delete by expression or using the primary key (int64).
        If chunk_ids are string UUIDs, we need to filter by chunk_id field.
        """
        client = self._get_client()
        name = collection_name or self.collection_name

        try:
            if self.provider == "milvus":
                # If we have the int64 PKs, we use delete(ids=[...])
                # If we only have chunk_ids (strings), we use delete(filter="chunk_id in ...")
                
                # Assume chunk_ids are the string identifiers
                ids_str = ", ".join([f'"{cid}"' for cid in chunk_ids])
                filter_expr = f'chunk_id in [{ids_str}]'
                
                res = client.delete(collection_name=name, filter=filter_expr)
                # res is usually a mutation result
                logger.info(f"Deleted chunks matching filter from collection '{name}'")
                return len(chunk_ids) # Approximate
            elif self.provider == "qdrant":
                # Qdrant delete by filter if chunk_ids are not point IDs
                from qdrant_client.models import Filter, FieldCondition, MatchAny
                
                client.delete(
                    collection_name=name,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="chunk_id",
                                match=MatchAny(any=chunk_ids)
                            )
                        ]
                    )
                )
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
                filter_expr = f'doc_id == "{doc_id}"'
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
                                    key="doc_id", # We stored doc_id in payload top level for Qdrant too
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
            
    def delete_by_kb_id(
        self,
        kb_id: str,
        collection_name: Optional[str] = None,
    ) -> bool:
        """Delete all chunks belonging to a knowledge base

        Args:
            kb_id: Knowledge Base ID
            collection_name: Name of collection

        Returns:
            True if successful
        """
        client = self._get_client()
        name = collection_name or self.collection_name

        try:
            if self.provider == "milvus":
                filter_expr = f'kb_id == "{kb_id}"'
                client.delete(collection_name=name, filter=filter_expr)
                logger.info(f"Deleted documents with kb_id '{kb_id}' from collection '{name}'")
                return True
            elif self.provider == "qdrant":
                from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector

                client.delete(
                    collection_name=name,
                    points_selector=FilterSelector(
                        filter=Filter(
                            must=[
                                FieldCondition(
                                    key="kb_id", 
                                    match=MatchValue(value=kb_id),
                                )
                            ]
                        )
                    ),
                )
                logger.info(f"Deleted documents with kb_id '{kb_id}' from collection '{name}'")
                return True
        except Exception as e:
            logger.error(f"Failed to delete kb {kb_id}: {e}")
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
