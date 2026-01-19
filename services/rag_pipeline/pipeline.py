"""RAG Pipeline - Main orchestration layer"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

from .loader.document_loader import DocumentLoader
from .chunker.text_chunker import TextChunker, Chunk
from .embedder.embedder import Embedder
from .retriever.retriever import Retriever
from .retriever.reranker import Reranker, NoOpReranker
from .store.vector_store import VectorStore, SearchResult

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG Pipeline for document ingestion and retrieval"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize RAG pipeline

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Initialize components
        self.loader = DocumentLoader(config)
        self.chunker = TextChunker(config)
        self.embedder = Embedder(config)
        self.vector_store = VectorStore(config)
        self.retriever = Retriever(config)

        # Initialize reranker
        rerank_config = config.get("reranker", {})
        if rerank_config.get("enabled", False):
            self.reranker = Reranker(config)
        else:
            self.reranker = NoOpReranker(config)

        # Get collection name
        vector_db_config = self.config.get("vector_db", self.config)
        self.collection_name = vector_db_config.get("collection", "knowledge_base")

        # Initialize collection
        self._initialize_collection()

    def _initialize_collection(self):
        """Initialize vector collection"""
        try:
            self.vector_store.create_collection(self.collection_name)
            logger.info(f"Initialized collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"Could not initialize collection: {e}")

    async def ingest_document(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingest a single document

        Args:
            file_path: Path to the document
            metadata: Optional metadata to attach

        Returns:
            Dictionary with ingestion results
        """
        try:
            # Load document
            doc = await self.loader.load(file_path)
            logger.info(f"Loaded document: {file_path}")

            # Prepare metadata
            doc_metadata = {**(metadata or {}), **doc.get("metadata", {})}

            # Split into chunks
            chunks = self.chunker.chunk(doc["content"], doc_metadata)
            logger.info(f"Created {len(chunks)} chunks")

            if not chunks:
                return {
                    "status": "success",
                    "file_path": file_path,
                    "chunks_created": 0,
                    "message": "No chunks created from document",
                }

            # Embed chunks
            embedded_chunks = await self.embedder.embed_chunks(chunks)
            logger.info(f"Generated {len(embedded_chunks)} embeddings")

            # Insert into vector store
            inserted = self.vector_store.insert(embedded_chunks, self.collection_name)

            # Index for BM25
            self.retriever.index_documents(embedded_chunks)

            return {
                "status": "success",
                "file_path": file_path,
                "chunks_created": len(chunks),
                "chunks_inserted": inserted,
                "doc_type": doc.get("type"),
            }

        except Exception as e:
            logger.error(f"Error ingesting document {file_path}: {e}")
            return {
                "status": "error",
                "file_path": file_path,
                "error": str(e),
            }

    async def ingest_documents(
        self,
        file_paths: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Ingest multiple documents

        Args:
            file_paths: List of file paths
            metadata: Optional metadata to attach to all documents

        Returns:
            List of ingestion results
        """
        results = []

        for file_path in file_paths:
            result = await self.ingest_document(file_path, metadata)
            results.append(result)

        # Summary
        successful = sum(1 for r in results if r.get("status") == "success")
        total_chunks = sum(r.get("chunks_created", 0) for r in results)

        logger.info(
            f"Ingested {successful}/{len(file_paths)} documents, "
            f"{total_chunks} total chunks"
        )

        return results

    async def ingest_text(
        self,
        text: str,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingest raw text

        Args:
            text: Text content
            doc_id: Document ID
            metadata: Optional metadata

        Returns:
            Ingestion result
        """
        try:
            # Split into chunks
            chunks = self.chunker.chunk(text, metadata)
            logger.info(f"Created {len(chunks)} chunks from text")

            if not chunks:
                return {
                    "status": "success",
                    "doc_id": doc_id,
                    "chunks_created": 0,
                }

            # Embed chunks
            embedded_chunks = await self.embedder.embed_chunks(chunks)

            # Insert into vector store
            inserted = self.vector_store.insert(embedded_chunks, self.collection_name)

            # Index for BM25
            self.retriever.index_documents(embedded_chunks)

            return {
                "status": "success",
                "doc_id": doc_id,
                "chunks_created": len(chunks),
                "chunks_inserted": inserted,
            }

        except Exception as e:
            logger.error(f"Error ingesting text {doc_id}: {e}")
            return {
                "status": "error",
                "doc_id": doc_id,
                "error": str(e),
            }

    async def search(
        self,
        query: str,
        top_k: int = 5,
        rerank: bool = False,
    ) -> List[SearchResult]:
        """Search for relevant documents

        Args:
            query: Search query
            top_k: Number of results to return
            rerank: Whether to apply reranking

        Returns:
            List of search results
        """
        try:
            # Embed query
            query_embedding = await self.embedder.embed_query(query)

            # Retrieve using hybrid search (get more for reranking)
            retrieve_k = top_k * 4 if rerank else top_k
            results = await self.retriever.retrieve(query, query_embedding, retrieve_k)

            # Apply reranking if requested
            if rerank:
                results = await self.reranker.rerank(query, results, top_n=top_k)

            return results[:top_k]

        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []

    async def ingest_directory(
        self,
        directory: str,
        pattern: str = "**/*",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Ingest all documents from a directory

        Args:
            directory: Directory path
            pattern: Glob pattern for files
            metadata: Optional metadata

        Returns:
            List of ingestion results
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            logger.error(f"Directory not found: {directory}")
            return []

        # Find files
        files = list(dir_path.glob(pattern))
        files = [f for f in files if f.is_file()]

        logger.info(f"Found {len(files)} files in {directory}")

        # Ingest all files
        file_paths = [str(f) for f in files]
        return await self.ingest_documents(file_paths, metadata)

    def delete_documents(self, chunk_ids: List[str]) -> int:
        """Delete documents by chunk IDs

        Args:
            chunk_ids: List of chunk IDs to delete

        Returns:
            Number of chunks deleted
        """
        return self.vector_store.delete(chunk_ids, self.collection_name)

    def drop_collection(self) -> bool:
        """Drop the entire collection

        Returns:
            True if successful
        """
        return self.vector_store.drop_collection(self.collection_name)

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics

        Returns:
            Dictionary with stats
        """
        count = self.vector_store.count(self.collection_name)

        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "config": {
                "chunker_strategy": self.chunker.strategy,
                "embedder_provider": self.embedder.provider,
                "embedder_model": self.embedder.model,
                "vector_db_provider": self.vector_store.provider,
            },
        }

    async def query(
        self,
        question: str,
        top_k: int = 5,
        context_template: str = "Context: {context}\n\nQuestion: {question}",
    ) -> Dict[str, Any]:
        """Query with context retrieval

        Args:
            question: Question to answer
            top_k: Number of context chunks to retrieve
            context_template: Template for formatting context

        Returns:
            Dictionary with context and results
        """
        # Search for relevant context
        results = await self.search(question, top_k=top_k)

        # Format context
        context_chunks = [r.content for r in results if r.content]
        context = "\n\n---\n\n".join(context_chunks)

        # Format with template
        formatted = context_template.format(context=context, question=question)

        return {
            "question": question,
            "context": context,
            "formatted_prompt": formatted,
            "results": results,
            "num_results": len(results),
        }
