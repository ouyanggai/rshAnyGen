"""Unit tests for RAG Pipeline"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from services.rag_pipeline.pipeline import RAGPipeline


@pytest.mark.unit
class TestRAGPipeline:
    """Test RAG Pipeline orchestration"""

    @pytest.fixture
    def config(self):
        """Test configuration"""
        return {
            "chunking": {
                "strategy": "simple",
                "child": {"size": 300, "overlap": 100},
            },
            "embedding": {
                "provider": "qwen",
                "model": "text-embedding-v3",
                "dimension": 1024,
                "qwen": {"api_key": "test-key"},
            },
            "vector_db": {
                "provider": "milvus",
                "host": "localhost",
                "port": 19530,
                "collection": "test_collection",
            },
            "retrieval": {
                "hybrid": True,
            },
        }

    @pytest.fixture
    def pipeline(self, config):
        """Create pipeline instance"""
        with patch("services.rag_pipeline.pipeline.VectorStore"):
            return RAGPipeline(config)

    def test_initialization(self, pipeline):
        """Test pipeline initialization"""
        assert pipeline.config is not None
        assert pipeline.loader is not None
        assert pipeline.chunker is not None
        assert pipeline.embedder is not None
        assert pipeline.vector_store is not None
        assert pipeline.retriever is not None
        assert pipeline.collection_name == "test_collection"

    @pytest.mark.asyncio
    async def test_ingest_text(self, pipeline):
        """Test text ingestion"""
        # Mock methods
        pipeline.embedder.embed_chunks = AsyncMock(return_value=[
            {"chunk_id": "chunk_0", "embedding": [0.1] * 1024, "content": "test"}
        ])
        pipeline.vector_store.insert = Mock(return_value=1)
        pipeline.retriever.index_documents = Mock()

        # Ingest text
        result = await pipeline.ingest_text("test document", "doc1")

        assert result["status"] == "success"
        assert result["doc_id"] == "doc1"
        assert result["chunks_created"] > 0
        assert result["chunks_inserted"] == 1

        # Verify mocks were called
        pipeline.embedder.embed_chunks.assert_called_once()
        pipeline.vector_store.insert.assert_called_once()
        pipeline.retriever.index_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_text_empty(self, pipeline):
        """Test text ingestion with empty text"""
        # Mock chunker to return empty list
        pipeline.chunker.chunk = Mock(return_value=[])

        result = await pipeline.ingest_text("", "doc1")

        assert result["status"] == "success"
        assert result["chunks_created"] == 0

    @pytest.mark.asyncio
    async def test_ingest_text_error(self, pipeline):
        """Test text ingestion with error"""
        # Mock embedder to raise error
        pipeline.embedder.embed_chunks = AsyncMock(side_effect=Exception("Embedding failed"))

        result = await pipeline.ingest_text("test", "doc1")

        assert result["status"] == "error"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_ingest_document(self, pipeline):
        """Test document ingestion from file"""
        # Mock loader
        pipeline.loader.load = AsyncMock(return_value={
            "type": "text",
            "content": "test content",
            "metadata": {"file_name": "test.txt"},
        })

        # Mock other components
        pipeline.embedder.embed_chunks = AsyncMock(return_value=[
            {"chunk_id": "chunk_0", "embedding": [0.1] * 1024, "content": "test"}
        ])
        pipeline.vector_store.insert = Mock(return_value=1)
        pipeline.retriever.index_documents = Mock()

        result = await pipeline.ingest_document("/path/to/test.txt")

        assert result["status"] == "success"
        assert result["file_path"] == "/path/to/test.txt"
        assert result["doc_type"] == "text"
        assert result["chunks_inserted"] == 1

    @pytest.mark.asyncio
    async def test_ingest_document_with_metadata(self, pipeline):
        """Test document ingestion with custom metadata"""
        # Mock loader
        pipeline.loader.load = AsyncMock(return_value={
            "type": "text",
            "content": "test content",
            "metadata": {"file_name": "test.txt"},
        })

        # Mock other components
        pipeline.embedder.embed_chunks = AsyncMock(return_value=[
            {"chunk_id": "chunk_0", "embedding": [0.1] * 1024, "content": "test"}
        ])
        pipeline.vector_store.insert = Mock(return_value=1)
        pipeline.retriever.index_documents = Mock()

        metadata = {"source": "test", "category": "demo"}
        result = await pipeline.ingest_document("/path/to/test.txt", metadata)

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_ingest_documents_batch(self, pipeline):
        """Test batch document ingestion"""
        # Mock loader
        pipeline.loader.load = AsyncMock(return_value={
            "type": "text",
            "content": "test content",
            "metadata": {"file_name": "test.txt"},
        })

        # Mock other components
        pipeline.embedder.embed_chunks = AsyncMock(return_value=[
            {"chunk_id": "chunk_0", "embedding": [0.1] * 1024, "content": "test"}
        ])
        pipeline.vector_store.insert = Mock(return_value=1)
        pipeline.retriever.index_documents = Mock()

        file_paths = ["/path/doc1.txt", "/path/doc2.txt"]
        results = await pipeline.ingest_documents(file_paths)

        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)

    @pytest.mark.asyncio
    async def test_search(self, pipeline):
        """Test document search"""
        # Mock embedder
        pipeline.embedder.embed_query = AsyncMock(return_value=[0.1] * 1024)

        # Mock retriever
        from services.rag_pipeline.store.vector_store import SearchResult
        mock_results = [
            SearchResult(
                chunk_id="chunk_0",
                content="test content",
                score=0.95,
                metadata={"index": 0},
            ),
            SearchResult(
                chunk_id="chunk_1",
                content="more content",
                score=0.85,
                metadata={"index": 1},
            ),
        ]
        pipeline.retriever.retrieve = AsyncMock(return_value=mock_results)

        results = await pipeline.search("test query", top_k=5)

        assert len(results) == 2
        assert results[0].chunk_id == "chunk_0"
        assert results[0].score == 0.95

        pipeline.embedder.embed_query.assert_called_once_with("test query")
        pipeline.retriever.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_error(self, pipeline):
        """Test search with error"""
        # Mock embedder to raise error
        pipeline.embedder.embed_query = AsyncMock(side_effect=Exception("Search failed"))

        results = await pipeline.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_query_with_context(self, pipeline):
        """Test query with context retrieval"""
        # Mock search
        pipeline.embedder.embed_query = AsyncMock(return_value=[0.1] * 1024)

        from services.rag_pipeline.store.vector_store import SearchResult
        mock_results = [
            SearchResult(
                chunk_id="chunk_0",
                content="relevant context",
                score=0.95,
            ),
        ]
        pipeline.retriever.retrieve = AsyncMock(return_value=mock_results)

        result = await pipeline.query("What is this about?", top_k=3)

        assert result["question"] == "What is this about?"
        assert "relevant context" in result["context"]
        assert result["num_results"] == 1
        assert "formatted_prompt" in result

    def test_delete_documents(self, pipeline):
        """Test document deletion"""
        pipeline.vector_store.delete = Mock(return_value=2)

        count = pipeline.delete_documents(["chunk_0", "chunk_1"])

        assert count == 2
        pipeline.vector_store.delete.assert_called_once()

    def test_drop_collection(self, pipeline):
        """Test collection deletion"""
        pipeline.vector_store.drop_collection = Mock(return_value=True)

        result = pipeline.drop_collection()

        assert result is True
        pipeline.vector_store.drop_collection.assert_called_once()

    def test_get_stats(self, pipeline):
        """Test statistics retrieval"""
        pipeline.vector_store.count = Mock(return_value=42)

        stats = pipeline.get_stats()

        assert stats["collection_name"] == "test_collection"
        assert stats["document_count"] == 42
        assert "config" in stats
        assert stats["config"]["chunker_strategy"] == "simple"
        assert stats["config"]["embedder_provider"] == "qwen"

    @pytest.mark.asyncio
    async def test_ingest_directory(self, pipeline, tmp_path):
        """Test directory ingestion"""
        # Create test files
        (tmp_path / "doc1.txt").write_text("content 1")
        (tmp_path / "doc2.txt").write_text("content 2")

        # Mock loader
        pipeline.loader.load = AsyncMock(return_value={
            "type": "text",
            "content": "test content",
            "metadata": {"file_name": "test.txt"},
        })

        # Mock other components
        pipeline.embedder.embed_chunks = AsyncMock(return_value=[
            {"chunk_id": "chunk_0", "embedding": [0.1] * 1024, "content": "test"}
        ])
        pipeline.vector_store.insert = Mock(return_value=1)
        pipeline.retriever.index_documents = Mock()

        results = await pipeline.ingest_directory(str(tmp_path))

        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)

    @pytest.mark.asyncio
    async def test_ingest_directory_not_found(self, pipeline):
        """Test directory ingestion with non-existent directory"""
        results = await pipeline.ingest_directory("/nonexistent/path")

        assert results == []
