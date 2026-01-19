"""聊天流式接口测试"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from apps.gateway.main import app

@pytest.mark.unit
@patch("apps.gateway.routers.chat.httpx.AsyncClient")
def test_chat_stream_forwarding(mock_client_cls):
    """测试：网关正确转发编排器的流式响应"""
    
    # 模拟编排器返回的数据行
    mock_lines = [
        json.dumps({"type": "thinking", "content": "Thinking..."}),
        json.dumps({"type": "chunk", "content": "Hello"}),
        json.dumps({"type": "chunk", "content": " World"}),
    ]
    
    # 模拟 response.aiter_lines
    async def mock_aiter_lines():
        for line in mock_lines:
            yield line
            
    # 构建 Mock 链
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines
    
    # 模拟 client.stream 上下文管理器
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
    
    # 模拟 client 上下文管理器
    mock_client = AsyncMock()
    mock_client.stream = MagicMock(return_value=mock_stream_ctx)
    mock_client_cls.return_value.__aenter__.return_value = mock_client
    
    # 发起请求
    client = TestClient(app)
    response = client.post("/api/v1/chat/stream", json={"message": "test"})
    
    # 验证响应状态
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # 验证流内容
    # TestClient.iter_lines() 返回的是解码后的行
    received_lines = list(response.iter_lines())
    
    # 过滤掉 keep-alive 等非数据行，解析 data
    data_lines = [line for line in received_lines if line.startswith("data: ")]
    
    assert len(data_lines) == 3 + 1 # 3 chunks + [DONE]
    
    # 验证第一行
    first_data = json.loads(data_lines[0].replace("data: ", ""))
    assert first_data["type"] == "thinking"
    assert first_data["content"] == "Thinking..."
    
    # 验证第二行
    second_data = json.loads(data_lines[1].replace("data: ", ""))
    assert second_data["type"] == "chunk"
    assert second_data["content"] == "Hello"

