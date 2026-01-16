"""Skills API 测试"""
import pytest
from fastapi.testclient import TestClient
from apps.gateway.main import app

@pytest.mark.unit
def test_list_skills():
    """测试：获取技能列表"""
    client = TestClient(app)
    response = client.get("/api/v1/skills")

    assert response.status_code == 200
    data = response.json()
    assert "skills" in data
    assert len(data["skills"]) == 3

    # 验证返回的技能
    skills = data["skills"]
    skill_ids = [s["id"] for s in skills]
    assert "web_search" in skill_ids
    assert "knowledge_query" in skill_ids

@pytest.mark.unit
def test_get_skill_found():
    """测试：获取存在的技能"""
    client = TestClient(app)
    response = client.get("/api/v1/skills/web_search")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "web_search"
    assert data["name"] == "网页搜索"
    assert data["enabled"] == True

@pytest.mark.unit
def test_get_skill_not_found():
    """测试：获取不存在的技能应返回 404"""
    client = TestClient(app)
    response = client.get("/api/v1/skills/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.unit
def test_toggle_skill_enable():
    """测试：启用技能"""
    client = TestClient(app)
    response = client.post("/api/v1/skills/code_interpreter/toggle", json={"enabled": True})

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] == True

@pytest.mark.unit
def test_toggle_skill_disable():
    """测试：禁用技能"""
    client = TestClient(app)
    response = client.post("/api/v1/skills/web_search/toggle", json={"enabled": False})

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] == False
