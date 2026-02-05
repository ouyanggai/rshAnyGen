import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apps.orchestrator.services.topic_detector import TopicDetector
from apps.orchestrator.services.summary_generator import SummaryGenerator

@pytest.fixture
def mock_embedding_client():
    mock = AsyncMock()
    # Mock embeddings: return different vectors
    # v1 = [1, 0], v2 = [0, 1] -> similarity 0
    # v1 = [1, 0], v2 = [1, 0] -> similarity 1
    mock.aembed_documents.return_value = [[1.0, 0.0], [1.0, 0.0]]
    return mock

@pytest.fixture
def mock_llm_client():
    mock = MagicMock()
    mock_model = AsyncMock()
    mock_model.ainvoke.return_value = MagicMock(content='{"topic": "Test", "content": "Summary"}')
    mock.get_chat_model.return_value = mock_model
    return mock

@pytest.mark.asyncio
async def test_topic_detection(mock_embedding_client):
    detector = TopicDetector(mock_embedding_client, threshold=0.8)
    
    # Case 1: High similarity
    mock_embedding_client.aembed_documents.return_value = [[1.0, 0.0], [0.9, 0.1]]
    is_changed = await detector.detect_topic_change(
        [{"role": "user", "content": "A"}, {"role": "user", "content": "B"}]
    )
    # 1.0 * 0.9 + 0 = 0.9 > 0.8 -> False (No change)
    assert not is_changed
    
    # Case 2: Low similarity
    mock_embedding_client.aembed_documents.return_value = [[1.0, 0.0], [0.0, 1.0]]
    is_changed = await detector.detect_topic_change(
        [{"role": "user", "content": "A"}, {"role": "user", "content": "B"}]
    )
    # 0 < 0.8 -> True (Changed)
    assert is_changed

@pytest.mark.asyncio
async def test_summary_generator(mock_llm_client, mock_embedding_client):
    with patch("apps.orchestrator.services.summary_generator.RedisOperations") as MockRedis:
        mock_redis = AsyncMock()
        MockRedis.return_value = mock_redis
        
        # Mock messages
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Bye"}
        ]
        mock_redis.lrange_json.return_value = messages
        
        # Mock detector to return 1 segment
        with patch("apps.orchestrator.services.summary_generator.TopicDetector.segment_by_topic") as mock_segment:
            mock_segment.return_value = [{
                "start_idx": 0, 
                "end_idx": 2, 
                "messages": messages,
                "topic": None
            }]
            
            generator = SummaryGenerator(mock_llm_client, mock_embedding_client)
            summaries = await generator.generate_summary("sess-1")
            
            assert len(summaries) == 1
            assert summaries[0]["topic"] == "Test"
            assert summaries[0]["summary"] == "Summary"
            
            # Verify redis save
            assert mock_redis.delete.called
            assert mock_redis.rpush_json.called
