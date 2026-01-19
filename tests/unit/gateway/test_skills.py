"""Skills API 测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from apps.gateway.main import app

# Mock registry response data
MOCK_REGISTRY_SKILLS = {
    "skills": [
        {
            "id": "web_search",
            "title": "网页搜索",
            "description": "搜索网页",
            "enabled": True,
            "category": "search"
        },
        {
            "id": "knowledge_query",
            "title": "知识库",
            "description": "查询知识",
            "enabled": True,
            "category": "knowledge"
        }
    ]
}

MOCK_SKILL_DETAIL = {
    "id": "web_search",
    "title": "网页搜索",
    "description": "搜索网页",
    "enabled": True,
    "category": "search"
}

@pytest.fixture
def mock_httpx_client():
    with patch("apps.gateway.routers.skills.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_client
        yield mock_client

@pytest.mark.unit
def test_list_skills(mock_httpx_client):
    """测试：获取技能列表"""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_REGISTRY_SKILLS
    mock_httpx_client.get.return_value = mock_response

    client = TestClient(app)
    response = client.get("/api/v1/skills")

    assert response.status_code == 200
    data = response.json()
    assert "skills" in data
    assert len(data["skills"]) == 2
    assert data["skills"][0]["id"] == "web_search"
    assert data["skills"][0]["name"] == "网页搜索"

@pytest.mark.unit
def test_get_skill_found(mock_httpx_client):
    """测试：获取存在的技能"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_SKILL_DETAIL
    mock_httpx_client.get.return_value = mock_response

    client = TestClient(app)
    response = client.get("/api/v1/skills/web_search")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "web_search"
    assert data["name"] == "网页搜索"

@pytest.mark.unit
def test_get_skill_not_found(mock_httpx_client):
    """测试：获取不存在的技能应返回 404"""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_httpx_client.get.return_value = mock_response

    client = TestClient(app)
    response = client.get("/api/v1/skills/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.unit
def test_toggle_skill(mock_httpx_client):
    """测试：启用/禁用技能"""
    # Reuse get_skill mock logic
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_SKILL_DETAIL
    mock_httpx_client.get.return_value = mock_response

    client = TestClient(app)
    # Toggle to False
    response = client.post("/api/v1/skills/web_search/toggle", json={"enabled": False})

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] == False
