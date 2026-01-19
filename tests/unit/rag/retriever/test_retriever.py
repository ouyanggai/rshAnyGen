"""Retriever Unit Tests"""

import pytest
from services.rag_pipeline.retriever.retriever import Retriever, BM25Index
from services.rag_pipeline.store.vector_store import SearchResult


@pytest.mark.unit
class TestBM25Index:
    """Test BM25Index"""

    def test_init_default_params(self):
        """Test initialization with default parameters"""
        index = BM25Index()

        assert index.k1 == 1.5
        assert index.b == 0.75
        assert index.doc_count == 0
        assert index.avg_doc_length == 0

    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        index = BM25Index(k1=1.2, b=0.8)

        assert index.k1 == 1.2
        assert index.b == 0.8

    def test_index_documents(self):
        """Test indexing documents"""
        index = BM25Index()

        docs = [
            {"chunk_id": "d1", "content": "hello world"},
            {"chunk_id": "d2", "content": "hello there"},
        ]

        index.index_documents(docs)

        assert index.doc_count == 2
        assert index.avg_doc_length > 0

    def test_index_empty_documents(self):
        """Test indexing empty document list"""
        index = BM25Index()

        index.index_documents([])

        assert index.doc_count == 0
        assert index.avg_doc_length == 0

    def test_search_returns_results(self):
        """Test search returns results"""
        index = BM25Index()

        docs = [
            {"chunk_id": "d1", "content": "hello world test"},
            {"chunk_id": "d2", "content": "goodbye world"},
        ]

        index.index_documents(docs)

        results = index.search("hello", top_k=5)

        assert isinstance(results, list)
        assert len(results) > 0
        assert isinstance(results[0], SearchResult)

    def test_search_no_matches(self):
        """Test search with no matching terms"""
        index = BM25Index()

        docs = [
            {"chunk_id": "d1", "content": "hello world"},
        ]

        index.index_documents(docs)

        results = index.search("xyz", top_k=5)

        # May return empty list or results with zero scores
        assert isinstance(results, list)

    def test_tokenize(self):
        """Test tokenization"""
        index = BM25Index()

        tokens = index._tokenize("Hello World")

        assert isinstance(tokens, list)
        assert len(tokens) > 0
        assert all(isinstance(t, str) for t in tokens)


@pytest.mark.unit
class TestRetriever:
    """Test Retriever"""

    def test_init_default_config(self):
        """Test initialization with default config"""
        retriever = Retriever()

        assert retriever.hybrid is True
        assert retriever.vector_top_k == 50
        assert retriever.bm25_top_k == 50
        assert retriever.fusion_method == "rrf"
        assert retriever.rrf_k == 60

    def test_init_custom_config(self):
        """Test initialization with custom config"""
        config = {
            "retrieval": {
                "hybrid": False,
                "vector_top_k": 10,
                "bm25_top_k": 20,
                "fusion_method": "weighted",
                "rrf_k": 30
            }
        }
        retriever = Retriever(config)

        assert retriever.hybrid is False
        assert retriever.vector_top_k == 10
        assert retriever.bm25_top_k == 20
        assert retriever.fusion_method == "weighted"
        assert retriever.rrf_k == 30

    def test_index_documents(self):
        """Test indexing documents"""
        retriever = Retriever()

        chunks = [
            {"chunk_id": "c1", "content": "text 1", "embedding": [0.0] * 1024},
            {"chunk_id": "c2", "content": "text 2", "embedding": [0.0] * 1024},
        ]

        # Mock vector store
        class MockVectorStore:
            def insert(self, chunks, collection_name=None):
                return len(chunks)

        retriever.vector_store = MockVectorStore()

        retriever.index_documents(chunks)

        # BM25 should have indexed
        assert retriever.bm25_index.doc_count == 2

    def test_rrf_fusion(self):
        """Test RRF fusion of results"""
        retriever = Retriever()

        vector_results = [
            SearchResult(chunk_id="c1", content="content 1", score=0.9),
            SearchResult(chunk_id="c2", content="content 2", score=0.8),
        ]

        bm25_results = [
            SearchResult(chunk_id="c2", content="content 2", score=0.7),
            SearchResult(chunk_id="c3", content="content 3", score=0.6),
        ]

        fused = retriever._rrf_fusion(vector_results, bm25_results, top_k=5)

        assert len(fused) == 3
        # c2 should rank highest (appears in both lists)
        assert fused[0].chunk_id == "c2"

    def test_rrf_fusion_empty_lists(self):
        """Test RRF fusion with empty result lists"""
        retriever = Retriever()

        fused = retriever._rrf_fusion([], [], top_k=5)

        assert fused == []

    def test_rrf_fusion_one_empty_list(self):
        """Test RRF fusion with one empty list"""
        retriever = Retriever()

        vector_results = [
            SearchResult(chunk_id="c1", content="content 1", score=0.9),
        ]

        fused = retriever._rrf_fusion(vector_results, [], top_k=5)

        assert len(fused) == 1
        assert fused[0].chunk_id == "c1"

    def test_reset(self):
        """Test resetting retriever state"""
        retriever = Retriever()

        chunks = [{"chunk_id": "c1", "content": "text", "embedding": [0.0] * 1024}]

        # Mock vector store
        class MockVectorStore:
            def insert(self, chunks, collection_name=None):
                pass

        retriever.vector_store = MockVectorStore()
        retriever.index_documents(chunks)

        assert retriever.bm25_index.doc_count == 1

        retriever.reset()

        assert retriever.bm25_index.doc_count == 0

    def test_direct_config_initialization(self):
        """Test initialization with direct config (not nested)"""
        config = {
            "hybrid": False,
            "vector_top_k": 15
        }
        retriever = Retriever(config)

        assert retriever.hybrid is False
        assert retriever.vector_top_k == 15
