"""RAG Pipeline Integration Tests"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from services.rag_pipeline.loader.document_loader import DocumentLoader
from services.rag_pipeline.chunker.text_chunker import TextChunker
from services.rag_pipeline.embedder.embedder import Embedder
from services.rag_pipeline.store.vector_store import VectorStore
from services.rag_pipeline.pipeline import RAGPipeline


@pytest.mark.integration
class TestRAGPipeline:
    """Test the complete RAG pipeline"""

    @pytest.mark.asyncio
    async def test_document_loading_text(self):
        """Test loading text documents"""
        loader = DocumentLoader()

        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is a test document.\n\nIt has multiple paragraphs.\n\nEach paragraph should be processed correctly.")
            temp_path = f.name

        try:
            result = await loader.load(temp_path)

            assert result["type"] == "text"
            assert "test document" in result["content"]
            assert result["metadata"]["format"] == ".txt"
            assert "file_name" in result["metadata"]
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_document_loading_markdown(self):
        """Test loading markdown documents"""
        loader = DocumentLoader()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Document\n\nThis is a **markdown** file.\n\n## Section 2\n\nMore content here.")
            temp_path = f.name

        try:
            result = await loader.load(temp_path)

            assert result["type"] == "text"
            assert "Test Document" in result["content"]
            assert result["metadata"]["format"] == ".md"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_text_chunking_simple(self):
        """Test simple text chunking"""
        chunker = TextChunker({"chunking": {"strategy": "simple", "child": {"size": 100}}})

        text = "This is a test document. " * 50  # Create a long text
        chunks = chunker.chunk(text, metadata={"source": "test"})

        assert len(chunks) > 1
        assert all(c.content for c in chunks)
        assert all(c.metadata.get("source") == "test" for c in chunks)

    @pytest.mark.asyncio
    async def test_text_chunking_parent_child(self):
        """Test parent-child chunking"""
        chunker = TextChunker({
            "chunking": {
                "strategy": "parent_child",
                "parent": {"size": 500, "overlap": 50},
                "child": {"size": 100, "overlap": 20}
            }
        })

        text = "This is a test document. " * 100
        chunks = chunker.chunk(text)

        # Should have parent and child chunks
        parent_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "parent"]
        child_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "child"]

        assert len(parent_chunks) > 0
        assert len(child_chunks) > 0
        assert all(c.parent_id for c in child_chunks)

    @pytest.mark.asyncio
    async def test_text_chunking_empty_text(self):
        """Test chunking empty text"""
        chunker = TextChunker()

        chunks = chunker.chunk("")
        assert chunks == []

        chunks = chunker.chunk("   ")
        assert chunks == []

    @pytest.mark.asyncio
    async def test_embedder_dimension(self):
        """Test embedder returns correct dimension"""
        embedder = Embedder({"embedding": {"dimension": 1024}})

        dimension = embedder.get_dimension()
        assert dimension == 1024

    @pytest.mark.asyncio
    async def test_embedder_verify_dimension(self):
        """Test embedder dimension verification"""
        embedder = Embedder({"embedding": {"dimension": 768}})

        valid_vector = [0.0] * 768
        invalid_vector = [0.0] * 512

        assert embedder.verify_dimension(valid_vector) is True
        assert embedder.verify_dimension(invalid_vector) is False

    @pytest.mark.asyncio
    async def test_vector_store_config(self):
        """Test vector store initialization"""
        config = {
            "vector_db": {
                "provider": "milvus",
                "host": "localhost",
                "port": 19530,
                "dimension": 1024
            }
        }
        store = VectorStore(config)

        assert store.provider == "milvus"
        assert store.host == "localhost"
        assert store.port == 19530
        assert store.dimension == 1024

    @pytest.mark.asyncio
    async def test_vector_store_search_empty(self, monkeypatch):
        """Test vector store handles empty results"""
        # Mock the client to avoid actual Milvus connection
        class MockClient:
            def has_collection(self, name):
                return True

            def search(self, **kwargs):
                return [[]]  # Empty results

        def mock_get_client(self):
            return MockClient()

        monkeypatch.setattr(VectorStore, "_get_client", mock_get_client)

        store = VectorStore()
        results = store.search([0.0] * 1024, top_k=5)

        assert results == []

    @pytest.mark.asyncio
    async def test_chunker_merge_chunks(self):
        """Test merging chunks back together"""
        chunker = TextChunker()

        from services.rag_pipeline.chunker.text_chunker import Chunk

        chunks = [
            Chunk(content="First part", chunk_id="child_0_0", parent_id="parent_0",
                  metadata={"chunk_type": "child", "child_index": 0}),
            Chunk(content="Second part", chunk_id="child_0_1", parent_id="parent_0",
                  metadata={"chunk_type": "child", "child_index": 1}),
        ]

        merged = chunker.merge_chunks(chunks)

        assert len(merged) == 1
        assert "First part" in merged[0]
        assert "Second part" in merged[0]

    @pytest.mark.asyncio
    async def test_document_loader_unsupported_type(self):
        """Test document loader with unsupported file type"""
        loader = DocumentLoader()

        with tempfile.NamedTemporaryFile(suffix=".unsupported", delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported file type"):
                await loader.load(temp_path)
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_document_loader_file_not_found(self):
        """Test document loader with non-existent file"""
        loader = DocumentLoader()

        with pytest.raises(FileNotFoundError):
            await loader.load("/nonexistent/path/to/file.txt")

    @pytest.mark.asyncio
    async def test_embedder_empty_texts(self):
        """Test embedder with empty text list"""
        embedder = Embedder()

        embeddings = await embedder.embed_documents([])
        assert embeddings == []

    @pytest.mark.asyncio
    async def test_chunker_custom_separators(self):
        """Test chunker with custom separators"""
        chunker = TextChunker({
            "chunking": {
                "strategy": "simple",
                "child": {"size": 10},  # Smaller than text to force splitting
                "separators": ["|||", "###"]
            }
        })

        text = "Part 1|||Part 2|||Part 3###Part 4"
        chunks = chunker.chunk(text)

        # Should split at custom separators
        assert len(chunks) > 1
        # Check that separators are used for splitting
        chunk_contents = [c.content for c in chunks]
        assert any("Part 1" in c for c in chunk_contents)
        assert any("Part 2" in c for c in chunk_contents)

    @pytest.mark.asyncio
    async def test_rag_pipeline_full_workflow(self):
        """Test complete RAG pipeline workflow"""
        # Mock vector store and embedder to avoid external dependencies
        with patch("pymilvus.MilvusClient"):
            # Create pipeline
            config = {
                "chunking": {
                    "strategy": "simple",
                    "child": {"size": 300, "overlap": 50},
                },
                "embedding": {
                    "provider": "qwen",
                    "model": "text-embedding-v3",
                    "dimension": 1024,
                },
                "vector_db": {
                    "provider": "milvus",
                    "collection": "test_collection",
                },
            }

            pipeline = RAGPipeline(config)

            # Mock embedder
            pipeline.embedder.embed_chunks = AsyncMock(return_value=[
                {"chunk_id": "chunk_0", "embedding": [0.1] * 1024, "content": "test"}
            ])

            # Test text ingestion
            result = await pipeline.ingest_text(
                "This is a test document for the RAG pipeline. " * 20,
                "test_doc_1",
                {"source": "integration_test"}
            )

            assert result["status"] == "success"
            assert result["doc_id"] == "test_doc_1"
            assert result["chunks_created"] > 0

            # Test stats
            stats = pipeline.get_stats()
            assert stats["collection_name"] == "test_collection"

    @pytest.mark.asyncio
    async def test_rag_pipeline_document_file_workflow(self):
        """Test RAG pipeline with file ingestion"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document content. " * 50)
            temp_path = f.name

        try:
            with patch("pymilvus.MilvusClient"):
                config = {
                    "chunking": {"strategy": "simple", "child": {"size": 200}},
                    "embedding": {"provider": "qwen", "dimension": 1024},
                    "vector_db": {"provider": "milvus", "collection": "test_file_col"},
                }

                pipeline = RAGPipeline(config)

                # Mock embedder
                pipeline.embedder.embed_chunks = AsyncMock(return_value=[
                    {"chunk_id": "chunk_0", "embedding": [0.1] * 1024, "content": "test"}
                ])

                result = await pipeline.ingest_document(temp_path)

                assert result["status"] == "success"
                assert result["file_path"] == temp_path
                assert result["doc_type"] == "text"
                assert result["chunks_created"] > 0

        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_rag_pipeline_batch_ingestion(self):
        """Test batch document ingestion"""
        with patch("pymilvus.MilvusClient"):
            config = {
                "chunking": {"strategy": "simple", "child": {"size": 100}},
                "embedding": {"provider": "qwen", "dimension": 1024},
                "vector_db": {"provider": "milvus", "collection": "batch_test"},
            }

            pipeline = RAGPipeline(config)

            # Mock embedder
            pipeline.embedder.embed_chunks = AsyncMock(return_value=[
                {"chunk_id": "chunk_0", "embedding": [0.1] * 1024, "content": "test"}
            ])

            # Ingest multiple texts
            texts = [
                ("First document content. " * 10, "doc1"),
                ("Second document content. " * 10, "doc2"),
                ("Third document content. " * 10, "doc3"),
            ]

            results = []
            for text, doc_id in texts:
                result = await pipeline.ingest_text(text, doc_id)
                results.append(result)

            assert all(r["status"] == "success" for r in results)
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_rag_pipeline_query_workflow(self):
        """Test query workflow with context retrieval"""
        with patch("pymilvus.MilvusClient"):
            from services.rag_pipeline.store.vector_store import SearchResult

            config = {
                "chunking": {"strategy": "simple", "child": {"size": 100}},
                "embedding": {"provider": "qwen", "dimension": 1024},
                "vector_db": {"provider": "milvus", "collection": "query_test"},
            }

            pipeline = RAGPipeline(config)

            # Mock search
            pipeline.embedder.embed_query = AsyncMock(return_value=[0.1] * 1024)
            pipeline.retriever.retrieve = AsyncMock(return_value=[
                SearchResult(
                    chunk_id="chunk_0",
                    content="Relevant context for the query",
                    score=0.95,
                    metadata={"index": 0},
                ),
                SearchResult(
                    chunk_id="chunk_1",
                    content="Additional context information",
                    score=0.85,
                    metadata={"index": 1},
                ),
            ])

            result = await pipeline.query("What is the main topic?")

            assert result["question"] == "What is the main topic?"
            assert "Relevant context" in result["context"]
            assert result["num_results"] == 2
            assert "formatted_prompt" in result
            assert "Context:" in result["formatted_prompt"]
            assert "Question:" in result["formatted_prompt"]

    @pytest.mark.asyncio
    async def test_rag_pipeline_search_workflow(self):
        """Test search workflow"""
        with patch("pymilvus.MilvusClient"):
            from services.rag_pipeline.store.vector_store import SearchResult

            config = {
                "chunking": {"strategy": "simple", "child": {"size": 100}},
                "embedding": {"provider": "qwen", "dimension": 1024},
                "vector_db": {"provider": "milvus", "collection": "search_test"},
            }

            pipeline = RAGPipeline(config)

            # Mock search
            pipeline.embedder.embed_query = AsyncMock(return_value=[0.1] * 1024)
            pipeline.retriever.retrieve = AsyncMock(return_value=[
                SearchResult(
                    chunk_id="chunk_0",
                    content="Search result 1",
                    score=0.92,
                ),
                SearchResult(
                    chunk_id="chunk_1",
                    content="Search result 2",
                    score=0.88,
                ),
            ])

            results = await pipeline.search("test query", top_k=5)

            assert len(results) == 2
            assert results[0].score == 0.92
            assert results[0].content == "Search result 1"
            assert results[1].score == 0.88

    @pytest.mark.asyncio
    async def test_rag_pipeline_error_handling(self):
        """Test error handling in pipeline"""
        with patch("pymilvus.MilvusClient"):
            config = {
                "chunking": {"strategy": "simple", "child": {"size": 100}},
                "embedding": {"provider": "qwen", "dimension": 1024},
                "vector_db": {"provider": "milvus", "collection": "error_test"},
            }

            pipeline = RAGPipeline(config)

            # Test with file that doesn't exist
            result = await pipeline.ingest_document("/nonexistent/file.txt")
            assert result["status"] == "error"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_rag_pipeline_chinese_text(self):
        """Test RAG pipeline with Chinese text"""
        with patch("pymilvus.MilvusClient"):
            config = {
                "chunking": {
                    "strategy": "simple",
                    "child": {"size": 100, "overlap": 20},
                },
                "embedding": {"provider": "qwen", "dimension": 1024},
                "vector_db": {"provider": "milvus", "collection": "chinese_test"},
            }

            pipeline = RAGPipeline(config)

            # Mock embedder
            pipeline.embedder.embed_chunks = AsyncMock(return_value=[
                {"chunk_id": "chunk_0", "embedding": [0.1] * 1024, "content": "test"}
            ])

            chinese_text = "这是一个中文文档。它包含多个句子。每个句子都应该被正确处理。" * 10

            result = await pipeline.ingest_text(chinese_text, "chinese_doc")

            assert result["status"] == "success"
            assert result["chunks_created"] > 0
