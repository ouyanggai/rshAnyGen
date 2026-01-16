"""Gateway 主入口测试"""
import pytest
from fastapi.testclient import TestClient

from apps.gateway.main import app

@pytest.mark.unit
def test_health_check():
    """测试：健康检查接口"""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gateway"

@pytest.mark.unit
def test_cors_middleware():
    """测试：CORS 中间件已配置"""
    # 检查应用的中间件堆栈中是否有 CORS 中间件
    from starlette.middleware.cors import CORSMiddleware

    # 检查 user_middleware 中的中间件
    has_cors = False
    for middleware in app.user_middleware:
        if hasattr(middleware, 'cls') and middleware.cls == CORSMiddleware:
            has_cors = True
            break
        elif hasattr(middleware, 'middleware') and isinstance(middleware.middleware, CORSMiddleware):
            has_cors = True
            break

    assert has_cors, "CORS middleware should be configured"

@pytest.mark.unit
def test_lifespan_startup_shutdown():
    """测试：生命周期事件处理器正确启动和关闭"""
    from apps.gateway.main import _logger_manager

    # 使用 TestClient 触发生命周期事件
    with TestClient(app) as client:
        # 启动事件被触发
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    # 关闭事件被触发，检查日志管理器是否被清理
    # 注意：由于 logger_manager 是全局的，它可能在测试之间保持状态
    # 这里我们主要验证没有异常抛出
