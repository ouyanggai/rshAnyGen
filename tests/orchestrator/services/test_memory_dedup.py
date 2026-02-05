import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from apps.orchestrator.services.memory_service import MemoryService

@pytest.fixture
def mock_milvus():
    with patch("apps.orchestrator.services.memory_service.connections") as mock_conn, \
         patch("apps.orchestrator.services.memory_service.Collection") as MockCollection, \
         patch("apps.orchestrator.services.memory_service.utility") as mock_util:
        
        mock_util.has_collection.return_value = True
        
        mock_collection = MagicMock()
        MockCollection.return_value = mock_collection
        
        yield mock_collection

@pytest.fixture
def mock_embedding_client():
    mock = AsyncMock()
    mock.aembed_query.return_value = [0.1] * 1536
    return mock

@pytest.mark.asyncio
async def test_save_memory_dedup(mock_milvus, mock_embedding_client):
    # Mock LLM Client to return our embedding client
    with patch("apps.orchestrator.services.memory_service.LLMClient") as MockLLM:
        MockLLM.return_value.get_embedding_client.return_value = mock_embedding_client
        
        service = MemoryService()
        
        # Case 1: No duplicate
        # mock search returns empty
        mock_milvus.search.return_value = [[]]
        
        await service.save_memory_with_dedup("u1", "test", 0.8, "s1")
        
        assert mock_milvus.insert.called
        
        # Case 2: Duplicate found
        # mock search returns a hit with high similarity
        mock_hit = MagicMock()
        mock_hit.id = 123
        mock_hit.distance = 0.95 # > 0.92
        mock_milvus.search.return_value = [[mock_hit]]
        
        mock_milvus.insert.reset_mock()
        await service.save_memory_with_dedup("u1", "test", 0.8, "s1")
        
        # Should NOT insert
        assert not mock_milvus.insert.called
