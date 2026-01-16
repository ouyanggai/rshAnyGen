"""会话管理中间件测试"""
import pytest
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from apps.gateway.middleware.session import SessionMiddleware


@pytest.mark.unit
def test_session_middleware_creates_session_id():
    """测试：无 session_id 时应创建新的"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    # 添加中间件（不连接 Redis）
    app.add_middleware(SessionMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"session_id": request.state.session_id}

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["session_id"].startswith("sess-")
    assert "X-Session-ID" in response.headers


@pytest.mark.unit
def test_session_middleware_uses_existing_session_id():
    """测试：有 session_id 时应使用现有的"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(SessionMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"session_id": request.state.session_id}

    existing_session = "sess-test123"
    client = TestClient(app)
    response = client.get("/test", headers={"X-Session-ID": existing_session})

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == existing_session
    assert response.headers["X-Session-ID"] == existing_session
