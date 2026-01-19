"""Embedder Unit Tests"""

import pytest
from services.rag_pipeline.embedder.embedder import Embedder


@pytest.mark.unit
class TestEmbedder:
    """Test Embedder"""

    def test_init_default_config(self):
        """Test initialization with default config"""
        embedder = Embedder()
        assert embedder.provider == "qwen"
        assert embedder.model == "text-embedding-v3"
        assert embedder.batch_size == 32
        assert embedder.dimension == 1024

    def test_init_custom_config(self):
        """Test initialization with custom config"""
        config = {
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "batch_size": 16,
                "dimension": 768
            }
        }
        embedder = Embedder(config)

        assert embedder.provider == "openai"
        assert embedder.model == "text-embedding-3-small"
        assert embedder.batch_size == 16
        assert embedder.dimension == 768

    def test_get_dimension(self):
        """Test getting embedding dimension"""
        embedder = Embedder({"embedding": {"dimension": 1536}})
        assert embedder.get_dimension() == 1536

    def test_verify_dimension_valid(self):
        """Test verifying correct dimension"""
        embedder = Embedder({"embedding": {"dimension": 768}})

        valid_vector = [0.0] * 768
        assert embedder.verify_dimension(valid_vector) is True

    def test_verify_dimension_invalid(self):
        """Test verifying incorrect dimension"""
        embedder = Embedder({"embedding": {"dimension": 768}})

        invalid_vector = [0.0] * 512
        assert embedder.verify_dimension(invalid_vector) is False

    def test_verify_dimension_empty(self):
        """Test verifying empty vector"""
        embedder = Embedder({"embedding": {"dimension": 768}})

        empty_vector = []
        assert embedder.verify_dimension(empty_vector) is False

    @pytest.mark.asyncio
    async def test_embed_documents_empty_list(self):
        """Test embedding empty document list"""
        embedder = Embedder()
        embeddings = await embedder.embed_documents([])

        assert embeddings == []

    @pytest.mark.asyncio
    async def test_embed_query_returns_list(self):
        """Test that embed_query returns a list"""
        embedder = Embedder({"embedding": {"dimension": 1024}})

        # Mock the LLM client to avoid actual API calls
        class MockClient:
            def embed_documents(self, texts):
                return [[0.0] * 1024 for _ in texts]

        embedder._llm_client = MockClient()

        result = await embedder.embed_query("test query")

        assert isinstance(result, list)
        assert len(result) == 1024

    @pytest.mark.asyncio
    async def test_embed_chunks(self):
        """Test embedding chunk objects"""
        from services.rag_pipeline.chunker.text_chunker import Chunk

        embedder = Embedder({"embedding": {"dimension": 512}})

        # Mock the LLM client
        class MockClient:
            def embed_documents(self, texts):
                return [[0.0] * 512 for _ in texts]

        embedder._llm_client = MockClient()

        chunks = [
            Chunk(content="Text 1", chunk_id="c1"),
            Chunk(content="Text 2", chunk_id="c2"),
        ]

        results = await embedder.embed_chunks(chunks)

        assert len(results) == 2
        assert results[0]["chunk_id"] == "c1"
        assert results[1]["chunk_id"] == "c2"
        assert all(len(r["embedding"]) == 512 for r in results)

    @pytest.mark.asyncio
    async def test_embed_chunks_dict_format(self):
        """Test embedding chunks in dict format"""
        embedder = Embedder({"embedding": {"dimension": 256}})

        # Mock the LLM client
        class MockClient:
            def embed_documents(self, texts):
                return [[0.0] * 256 for _ in texts]

        embedder._llm_client = MockClient()

        chunks = [
            {"content": "Text 1", "id": "c1"},
            {"content": "Text 2", "id": "c2"},
        ]

        results = await embedder.embed_chunks(chunks)

        assert len(results) == 2
        assert results[0]["id"] == "c1"
        assert results[1]["id"] == "c2"

    def test_qwen_config(self):
        """Test Qwen provider configuration"""
        config = {
            "embedding": {
                "provider": "qwen",
                "qwen": {
                    "base_url": "https://api.qwen.com",
                    "api_key": "test-key"
                }
            }
        }
        embedder = Embedder(config)

        assert embedder.qwen_config["base_url"] == "https://api.qwen.com"
        assert embedder.qwen_config["api_key"] == "test-key"

    def test_openai_config(self):
        """Test OpenAI provider configuration"""
        config = {
            "embedding": {
                "provider": "openai",
                "openai": {
                    "api_key": "sk-test"
                }
            }
        }
        embedder = Embedder(config)

        assert embedder.openai_config["api_key"] == "sk-test"
