"""聊天接口测试"""
import pytest
from fastapi.testclient import TestClient
from apps.gateway.main import app


@pytest.mark.unit
def test_chat_stream_endpoint_exists():
    """测试：聊天流式接口存在"""
    client = TestClient(app)
    response = client.post("/api/v1/chat/stream", json={
        "message": "test"
    })

    # 预期：503（Orchestrator 未运行）或 200（模拟成功）
    assert response.status_code in [200, 503]


@pytest.mark.unit
def test_chat_stream_with_session_id():
    """测试：聊天接口使用会话 ID"""
    client = TestClient(app)
    session_id = "sess-test123"
    response = client.post(
        "/api/v1/chat/stream",
        json={"message": "hello"},
        headers={"X-Session-ID": session_id}
    )

    # 验证响应头包含 session_id
    assert "X-Session-ID" in response.headers
    assert response.status_code in [200, 503]


@pytest.mark.unit
def test_chat_stream_creates_session():
    """测试：聊天接口自动创建会话"""
    client = TestClient(app)
    response = client.post("/api/v1/chat/stream", json={
        "message": "test"
    })

    # 验证响应头包含新创建的 session_id
    assert "X-Session-ID" in response.headers
    if response.status_code == 200:
        assert response.headers["X-Session-ID"].startswith("sess-")
