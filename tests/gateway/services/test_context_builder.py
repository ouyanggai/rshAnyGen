import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from apps.gateway.services.context_builder import ContextBuilder

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    # Setup default behaviors
    mock.hgetall.return_value = {}
    mock.smembers.return_value = set()
    mock.lrange_json.return_value = []
    return mock

@pytest.fixture
def context_builder(mock_redis):
    with patch("apps.gateway.services.context_builder.RedisOperations") as MockRedis:
        # Return our mock instance when RedisOperations() is called
        MockRedis.return_value = mock_redis
        builder = ContextBuilder("qwen-max")
        # Ensure the builder uses our mock
        builder._redis = mock_redis
        return builder

@pytest.mark.asyncio
async def test_build_context_basic(context_builder, mock_redis):
    # Setup data
    mock_redis.lrange_json.return_value = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"}
    ]
    
    context = await context_builder.build_context("sess-1", "user-1", "How are you?")
    
    # Should have 3 messages: 2 from history + 1 current
    assert len(context) == 3
    assert context[-1]["content"] == "How are you?"

@pytest.mark.asyncio
async def test_build_context_with_memory_and_summary(context_builder, mock_redis):
    # Setup User Memory
    # hgetall for user:user-1 returns profile
    # lrange_json for session:summaries:sess-1 returns summary
    # lrange_json for session:messages:sess-1 returns []
    
    async def lrange_side_effect(key, start, end):
        if "summaries" in key:
            return [{"topic": "Intro", "summary": "User introduced himself"}]
        return []

    mock_redis.hgetall.side_effect = lambda k: {"nickname": "Tester"} if "user:" in k else {}
    mock_redis.smembers.return_value = {"coder"}
    mock_redis.lrange_json.side_effect = lrange_side_effect
    
    context = await context_builder.build_context("sess-1", "user-1", "Next")
    
    # Should have:
    # 1. System (User Profile)
    # 2. System (Summary)
    # 3. User (Current)
    assert len(context) == 3
    assert context[0]["role"] == "system"
    assert "Tester" in context[0]["content"]
    assert "Intro" in context[1]["content"]

@pytest.mark.asyncio
async def test_context_budget_fallback(context_builder, mock_redis):
    # Mock TokenCounter to return specific budget
    with patch("apps.shared.token_counter.TokenCounter.get_token_budget") as mock_budget:
        mock_budget.return_value = {
            "total": 1000,
            "available_for_context": 900,
            "long_term": 100,
            "short_term": 100,
            "working": 700
        }
        
        # No long term memory or summary -> budget should flow to working memory
        mock_redis.hgetall.return_value = {}
        # Provide plenty of messages to trigger trimming
        # Each message "msg" is small, so we need many to exceed 700 tokens?
        # Or we rely on trim_messages_to_limit receiving the increased max_tokens.
        
        # 100 msgs * ~5 tokens = 500 tokens. Not enough to exceed 700.
        # We need large messages.
        long_msg = "a" * 100 # ~25 tokens
        msgs = [{"role": "user", "content": long_msg} for _ in range(50)]
        mock_redis.lrange_json.return_value = msgs
        
        # Mocking trim_messages_to_limit to check if max_tokens increased
        with patch.object(context_builder.token_counter, 'trim_messages_to_limit') as mock_trim:
            mock_trim.return_value = []
            
            await context_builder.build_context("sess-1", "user-1", "msg")
            
            # 700 (working) + 100 (unused long) + 100 (unused short) = 900
            # minus current message tokens (approx 5)
            # max_tokens passed to trim should be around 895 > 700
            
            assert mock_trim.called
            call_args = mock_trim.call_args
            assert call_args.kwargs["max_tokens"] > 800
