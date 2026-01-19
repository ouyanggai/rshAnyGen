"""Reranker Unit Tests"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.rag_pipeline.retriever.reranker import Reranker, NoOpReranker
from services.rag_pipeline.store.vector_store import SearchResult


@pytest.mark.unit
class TestReranker:
    """Test Reranker"""

    @pytest.fixture
    def config(self):
        return {
            "reranker": {
                "provider": "qwen",
                "model": "rerank-v2",
                "top_n": 5,
                "api_key": "test-key",
            }
        }

    @pytest.fixture
    def sample_results(self):
        return [
            SearchResult(
                chunk_id="chunk_0",
                content="First result about AI",
                score=0.85,
                metadata={"index": 0},
            ),
            SearchResult(
                chunk_id="chunk_1",
                content="Second result about machine learning",
                score=0.75,
                metadata={"index": 1},
            ),
            SearchResult(
                chunk_id="chunk_2",
                content="Third result about deep learning",
                score=0.65,
                metadata={"index": 2},
            ),
        ]

    def test_init_default_config(self):
        """Test initialization with default config"""
        reranker = Reranker()
        assert reranker.provider == "qwen"
        assert reranker.model == "rerank-v2"
        assert reranker.top_n == 5

    def test_init_custom_config(self, config):
        """Test initialization with custom config"""
        reranker = Reranker(config)
        assert reranker.provider == "qwen"
        assert reranker.model == "rerank-v2"
        assert reranker.top_n == 5
        assert reranker.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_rerank_empty_results(self, config):
        """Test reranking with empty results"""
        reranker = Reranker(config)
        results = await reranker.rerank("test query", [])
        assert results == []

    @pytest.mark.asyncio
    async def test_rerank_with_qwen_mock(self, config, sample_results):
        """Test reranking with Qwen API mock"""
        reranker = Reranker(config)

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": {
                "results": [
                    {"index": 2, "relevance_score": 0.95},  # Third result becomes first
                    {"index": 0, "relevance_score": 0.85},  # First result stays
                    {"index": 1, "relevance_score": 0.70},  # Second result drops
                ]
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            results = await reranker.rerank("AI and machine learning", sample_results, top_n=3)

            assert len(results) == 3
            assert results[0].chunk_id == "chunk_2"  # Reordered
            assert results[0].score == 0.95  # New rerank score

    @pytest.mark.asyncio
    async def test_rerank_fallback_on_error(self, config, sample_results):
        """Test fallback to original results on error"""
        reranker = Reranker(config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("API error")
            )

            results = await reranker.rerank("test query", sample_results, top_n=2)

            # Should return original top results
            assert len(results) == 2
            assert results[0].chunk_id == "chunk_0"
            assert results[1].chunk_id == "chunk_1"


@pytest.mark.unit
class TestNoOpReranker:
    """Test NoOpReranker"""

    @pytest.fixture
    def sample_results(self):
        return [
            SearchResult(chunk_id="chunk_0", content="First", score=0.9),
            SearchResult(chunk_id="chunk_1", content="Second", score=0.8),
            SearchResult(chunk_id="chunk_2", content="Third", score=0.7),
        ]

    def test_init_default_config(self):
        """Test initialization with default config"""
        reranker = NoOpReranker()
        assert reranker.top_n == 5

    def test_init_custom_config(self):
        """Test initialization with custom config"""
        reranker = NoOpReranker({"top_n": 3})
        assert reranker.top_n == 3

    @pytest.mark.asyncio
    async def test_rerank_returns_top_n(self, sample_results):
        """Test that no-op reranker returns top N results"""
        reranker = NoOpReranker({"top_n": 2})

        results = await reranker.rerank("query", sample_results)

        assert len(results) == 2
        assert results[0].chunk_id == "chunk_0"
        assert results[1].chunk_id == "chunk_1"

    @pytest.mark.asyncio
    async def test_rerank_with_custom_top_n(self, sample_results):
        """Test no-op reranker with custom top_n"""
        reranker = NoOpReranker({"top_n": 5})

        results = await reranker.rerank("query", sample_results, top_n=1)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_rerank_empty_results(self):
        """Test no-op reranker with empty results"""
        reranker = NoOpReranker()

        results = await reranker.rerank("query", [])

        assert results == []
