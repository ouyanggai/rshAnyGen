import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apps.orchestrator.services.entity_extractor import EntityExtractor
from apps.orchestrator.models.entity import Entity

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    return mock

@pytest.fixture
def mock_llm_client():
    mock = MagicMock()
    return mock

@pytest.mark.asyncio
async def test_entity_extraction_rules(mock_redis, mock_llm_client):
    with patch("apps.orchestrator.services.entity_extractor.RedisOperations") as MockRedis:
        MockRedis.return_value = mock_redis
        
        extractor = EntityExtractor(mock_llm_client)
        
        # Test rule matching
        text = "我叫张三，是一个程序员。"
        entities = await extractor.extract_entities(text, "", "user-1", "sess-1")
        
        assert len(entities) == 1
        assert entities[0].type == "person"
        assert entities[0].name == "张三"
        
        # Verify save
        assert mock_redis.hset.called
        assert mock_redis.zadd.called

@pytest.mark.asyncio
async def test_entity_extraction_llm(mock_redis, mock_llm_client):
    with patch("apps.orchestrator.services.entity_extractor.RedisOperations") as MockRedis:
        MockRedis.return_value = mock_redis
        
        # Mock LLM response
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value = MagicMock(content='{"entities": [{"type": "project", "name": "Alpha", "confidence": 0.9}]}')
        mock_llm_client.get_chat_model.return_value = mock_model
        
        extractor = EntityExtractor(mock_llm_client)
        
        # Test LLM extraction (text > 10 chars)
        text = "这是一个非常复杂的项目，它的名字是Alpha。"
        entities = await extractor.extract_entities(text, "", "user-1", "sess-1")
        
        # Should have 1 entity (LLM) + maybe rule matches
        # "名字是Alpha" might match rule? 
        # Rule: (?:项目|系统|产品)(?:叫|名为)\s*(\w{2,20})
        # "名字是" not in rule. Rule is "叫" or "名为".
        # So only LLM should find it.
        
        assert len(entities) >= 1
        names = [e.name for e in entities]
        assert "Alpha" in names
