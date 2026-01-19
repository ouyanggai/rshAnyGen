"""Vector Store Unit Tests"""

import pytest
from services.rag_pipeline.store.vector_store import VectorStore, SearchResult


@pytest.mark.unit
class TestVectorStore:
    """Test VectorStore"""

    def test_init_default_config(self):
        """Test initialization with default config"""
        store = VectorStore()
        assert store.provider == "milvus"
        assert store.host == "localhost"
        assert store.port == 19530
        assert store.collection_name == "knowledge_base"
        assert store.dimension == 1024

    def test_init_custom_config(self):
        """Test initialization with custom config"""
        config = {
            "vector_db": {
                "provider": "milvus",
                "host": "remote.host",
                "port": 9090,
                "collection": "test_collection",
                "dimension": 768,
                "index_type": "IVF",
                "metric_type": "L2"
            }
        }
        store = VectorStore(config)

        assert store.provider == "milvus"
        assert store.host == "remote.host"
        assert store.port == 9090
        assert store.collection_name == "test_collection"
        assert store.dimension == 768
        assert store.index_type == "IVF"
        assert store.metric_type == "L2"

    def test_init_with_direct_config(self):
        """Test initialization with direct config (not nested)"""
        config = {
            "provider": "milvus",
            "host": "example.com",
            "port": 8080,
            "collection": "docs"
        }
        store = VectorStore(config)

        assert store.provider == "milvus"
        assert store.host == "example.com"
        assert store.collection_name == "docs"

    def test_create_collection_unsupported_provider(self):
        """Test create_collection with unsupported provider"""
        store = VectorStore({"vector_db": {"provider": "unsupported"}})

        with pytest.raises(ValueError, match="Unsupported vector DB provider"):
            store._get_client()

    def test_insert_empty_list(self):
        """Test inserting empty chunk list"""
        # Mock client
        class MockClient:
            pass

        store = VectorStore()
        store._client = MockClient()

        count = store.insert([])

        assert count == 0

    def test_insert_returns_count(self):
        """Test insert returns correct count"""
        # Mock client
        class MockClient:
            def insert(self, collection_name, data):
                pass

        store = VectorStore()
        store._client = MockClient()

        chunks = [
            {"chunk_id": "c1", "embedding": [0.0] * 1024, "content": "text1"},
            {"chunk_id": "c2", "embedding": [0.0] * 1024, "content": "text2"},
        ]

        count = store.insert(chunks)

        assert count == 2

    def test_search_returns_list(self):
        """Test search returns list of results"""
        # Mock client
        class MockClient:
            def search(self, collection_name, data, limit, output_fields):
                return [[
                    {"id": "c1", "distance": 0.5, "text": "result text", "metadata": {}}
                ]]

        store = VectorStore()
        store._client = MockClient()

        results = store.search([0.0] * 1024, top_k=5)

        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].chunk_id == "c1"
        assert results[0].score == 0.5

    def test_search_empty_results(self):
        """Test search with empty results"""
        # Mock client
        class MockClient:
            def search(self, collection_name, data, limit, output_fields):
                return [[]]

        store = VectorStore()
        store._client = MockClient()

        results = store.search([0.0] * 1024, top_k=5)

        assert results == []

    def test_delete_returns_count(self):
        """Test delete returns correct count"""
        # Mock client
        class MockClient:
            def delete(self, collection_name, ids):
                pass

        store = VectorStore()
        store._client = MockClient()

        count = store.delete(["c1", "c2", "c3"])

        assert count == 3

    def test_drop_collection(self):
        """Test dropping collection"""
        # Mock client
        class MockClient:
            def drop_collection(self, collection_name):
                pass

        store = VectorStore()
        store._client = MockClient()

        result = store.drop_collection()

        assert result is True

    def test_count_defaults_to_zero(self):
        """Test count returns zero when client fails"""
        # Mock client
        class MockClient:
            def get_collection_stats(self, collection_name):
                raise Exception("Not connected")

        store = VectorStore()
        store._client = MockClient()

        count = store.count()

        assert count == 0


@pytest.mark.unit
class TestSearchResult:
    """Test SearchResult dataclass"""

    def test_create_search_result(self):
        """Test creating a SearchResult"""
        result = SearchResult(
            chunk_id="test_id",
            content="test content",
            score=0.85,
            metadata={"key": "value"}
        )

        assert result.chunk_id == "test_id"
        assert result.content == "test content"
        assert result.score == 0.85
        assert result.metadata == {"key": "value"}

    def test_create_search_result_without_metadata(self):
        """Test creating SearchResult without optional metadata"""
        result = SearchResult(
            chunk_id="test_id",
            content="test content",
            score=0.5
        )

        assert result.chunk_id == "test_id"
        assert result.content == "test content"
        assert result.score == 0.5
        assert result.metadata is None
