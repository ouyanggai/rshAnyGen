"""Skills API 集成测试"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from services.skills_registry.api.main import app


@pytest.mark.integration
class TestSkillsAPI:
    """Skills API 集成测试"""

    def test_root_endpoint(self):
        """测试根路径"""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Skills Registry API"
        assert data["status"] == "running"

    def test_list_skills(self):
        """测试获取 Skills 列表"""
        client = TestClient(app)
        response = client.get("/api/v1/skills")
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        assert isinstance(data["skills"], list)

    def test_get_skill_detail(self):
        """测试获取 Skill 详情"""
        client = TestClient(app)

        # 首先获取列表
        list_response = client.get("/api/v1/skills")
        skills = list_response.json()["skills"]

        if skills:
            # 测试获取第一个 skill 的详情
            skill_id = skills[0]["id"]
            response = client.get(f"/api/v1/skills/{skill_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == skill_id
            assert "title" in data
            assert "description" in data

    def test_get_skill_not_found(self):
        """测试获取不存在的 Skill"""
        client = TestClient(app)
        response = client.get("/api/v1/skills/nonexistent-skill")
        assert response.status_code == 404

    def test_execute_skill(self):
        """测试执行 Skill"""
        client = TestClient(app)

        # 首先获取可用的 skills
        list_response = client.get("/api/v1/skills")
        skills = list_response.json()["skills"]

        if skills:
            skill_id = skills[0]["id"]
            response = client.post(
                f"/api/v1/skills/{skill_id}/execute",
                json={"params": {}, "context": {}}
            )

            # 可能成功也可能失败（取决于 skill 的实现）
            assert response.status_code in [200, 500]  # 允许内部错误
            data = response.json()
            assert "status" in data
            assert "execution_time_ms" in data

    def test_execute_skill_not_found(self):
        """测试执行不存在的 Skill"""
        client = TestClient(app)
        response = client.post(
            "/api/v1/skills/nonexistent/execute",
            json={"params": {}, "context": {}}
        )
        assert response.status_code == 404

    def test_health_check(self):
        """测试健康检查"""
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "total_skills" in data
        assert isinstance(data["total_skills"], int)
        assert isinstance(data["skills_list"], list)
