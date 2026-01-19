"""Retriever - Hybrid search with vector and BM25"""

from typing import List, Dict, Any, Optional
import logging
import math
from collections import defaultdict

from ..store.vector_store import VectorStore, SearchResult

logger = logging.getLogger(__name__)


class BM25Index:
    """Simple BM25 index for keyword search"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """Initialize BM25 index

        Args:
            k1: Term frequency saturation parameter
            b: Length normalization parameter
        """
        self.k1 = k1
        self.b = b
        self.doc_count = 0
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.doc_freqs = defaultdict(int)  # Document frequency
        self.inverted_index = defaultdict(lambda: defaultdict(int))  # Term -> Doc -> Count

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Index documents for BM25 search

        Args:
            documents: List of documents with chunk_id and content
        """
        self.doc_count = len(documents)
        total_length = 0

        for doc in documents:
            doc_id = doc.get("chunk_id", "")
            content = doc.get("content", "")
            terms = self._tokenize(content)

            doc_length = len(terms)
            self.doc_lengths.append(doc_length)
            total_length += doc_length

            # Track unique terms for this doc
            seen_terms = set()

            for term in terms:
                self.inverted_index[term][doc_id] += 1
                if term not in seen_terms:
                    self.doc_freqs[term] += 1
                    seen_terms.add(term)

        self.avg_doc_length = total_length / self.doc_count if self.doc_count > 0 else 0
        logger.info(f"Indexed {self.doc_count} documents for BM25")

    def _tokenize(self, text: str) -> List[str]:
        """Tokenization for Chinese and English using jieba

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        try:
            import jieba

            # Use jieba for Chinese word segmentation
            words = jieba.lcut(text)
            # Filter out empty strings and single punctuation
            tokens = [w.lower().strip() for w in words if w.strip() and len(w.strip()) > 1]
            return tokens
        except ImportError:
            logger.warning("jieba not installed, using basic tokenization. Run: pip install jieba")
            # Fallback to character-level tokenization
            tokens = []
            for char in text:
                if char.strip():
                    tokens.append(char.lower())
            return tokens

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Search using BM25 scoring

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of search results with BM25 scores
        """
        terms = self._tokenize(query)
        scores = defaultdict(float)

        for term in terms:
            if term not in self.inverted_index:
                continue

            # IDF calculation
            idf = math.log(
                (self.doc_count - self.doc_freqs[term] + 0.5) / (self.doc_freqs[term] + 0.5) + 1
            )

            for doc_id, term_freq in self.inverted_index[term].items():
                # Get doc length
                doc_idx = int(doc_id.split("_")[-1]) if "_" in doc_id else 0
                doc_length = self.doc_lengths[doc_idx] if doc_idx < len(self.doc_lengths) else self.avg_doc_length

                # BM25 score
                numerator = term_freq * (self.k1 + 1)
                denominator = term_freq + self.k1 * (
                    1 - self.b + self.b * (doc_length / self.avg_doc_length)
                )

                scores[doc_id] += idf * (numerator / denominator)

        # Sort and return top results
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return [
            SearchResult(
                chunk_id=doc_id,
                content="",  # Would need to lookup from original docs
                score=score,
            )
            for doc_id, score in sorted_results
        ]


class Retriever:
    """Hybrid retriever combining vector search and BM25"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize retriever

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Get retrieval settings
        retrieval_config = self.config.get("retrieval", self.config)
        self.hybrid = retrieval_config.get("hybrid", True)
        self.vector_top_k = retrieval_config.get("vector_top_k", 50)
        self.bm25_top_k = retrieval_config.get("bm25_top_k", 50)
        self.fusion_method = retrieval_config.get("fusion_method", "rrf")
        self.rrf_k = retrieval_config.get("rrf_k", 60)

        # Initialize components
        self.vector_store = VectorStore(config)
        self.bm25_index = BM25Index()

    def index_documents(self, chunks: List[Dict[str, Any]]) -> None:
        """Index documents for hybrid search

        Args:
            chunks: List of chunks with embeddings and content
        """
        # Note: Vector store insertion is handled by the pipeline
        
        # Index for BM25
        self.bm25_index.index_documents(chunks)

    async def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[SearchResult]:
        """Retrieve relevant chunks using hybrid search

        Args:
            query: Query text
            query_embedding: Query vector
            top_k: Number of results to return

        Returns:
            List of search results
        """
        if self.hybrid:
            return await self._hybrid_retrieve(query, query_embedding, top_k)
        else:
            return await self._vector_retrieve(query_embedding, top_k)

    async def _vector_retrieve(
        self,
        query_embedding: List[float],
        top_k: int,
    ) -> List[SearchResult]:
        """Vector-only retrieval

        Args:
            query_embedding: Query vector
            top_k: Number of results

        Returns:
            List of search results
        """
        results = self.vector_store.search(query_embedding, top_k=top_k)
        return results

    async def _hybrid_retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int,
    ) -> List[SearchResult]:
        """Hybrid retrieval combining vector and BM25

        Args:
            query: Query text
            query_embedding: Query vector
            top_k: Number of results

        Returns:
            List of fused search results
        """
        # Get vector results
        vector_results = self.vector_store.search(query_embedding, top_k=self.vector_top_k)

        # Get BM25 results
        bm25_results = self.bm25_index.search(query, top_k=self.bm25_top_k)

        # Fusion
        if self.fusion_method == "rrf":
            return self._rrf_fusion(vector_results, bm25_results, top_k)
        else:
            # Default to vector results
            return vector_results[:top_k]

    def _rrf_fusion(
        self,
        vector_results: List[SearchResult],
        bm25_results: List[SearchResult],
        top_k: int,
    ) -> List[SearchResult]:
        """Reciprocal Rank Fusion (RRF)

        Args:
            vector_results: Vector search results
            bm25_results: BM25 search results
            top_k: Number of results to return

        Returns:
            Fused results
        """
        # Score dictionaries
        scores = defaultdict(float)
        content_map = {}
        metadata_map = {}

        # Add vector scores
        for rank, result in enumerate(vector_results, 1):
            rrf_score = 1.0 / (self.rrf_k + rank)
            scores[result.chunk_id] += rrf_score
            content_map[result.chunk_id] = result.content
            metadata_map[result.chunk_id] = result.metadata

        # Add BM25 scores
        for rank, result in enumerate(bm25_results, 1):
            rrf_score = 1.0 / (self.rrf_k + rank)
            scores[result.chunk_id] += rrf_score
            if result.content:
                content_map[result.chunk_id] = result.content
            if result.metadata:
                metadata_map[result.chunk_id] = result.metadata

        # Sort by combined score
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return [
            SearchResult(
                chunk_id=doc_id,
                content=content_map.get(doc_id, ""),
                score=score,
                metadata=metadata_map.get(doc_id),
            )
            for doc_id, score in sorted_results
        ]

    def reset(self) -> None:
        """Reset the retriever state"""
        self.bm25_index = BM25Index()
