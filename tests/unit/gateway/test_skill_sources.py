"""Skill Sources API 测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.gateway.main import app


MOCK_SOURCES = {
    "sources": [
        {
            "id": "vercel-skills",
            "name": "Vercel Labs Skills",
            "repo_url": "https://github.com/vercel-labs/skills.git",
            "subdir": "skills",
            "ref": None,
            "enabled": True,
            "builtin": True,
            "description": "Vercel Labs 出品的 skills",
        }
    ]
}

MOCK_ALL_SKILLS = {
    "skills": [
        {
            "source_id": "vercel-skills",
            "source_name": "Vercel Labs Skills",
            "id": "find-skills",
            "slug": "find-skills",
            "title": "Find Skills",
            "description": "desc",
            "installed": False,
            "execution_type": "prompt",
        }
    ],
    "errors": [],
}


@pytest.fixture
def mock_httpx_client():
    with patch("apps.gateway.routers.skill_sources.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_client
        yield mock_client


@pytest.mark.unit
def test_list_skill_sources(mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_SOURCES
    mock_httpx_client.get.return_value = mock_response

    client = TestClient(app)
    response = client.get("/api/v1/skill-sources", headers={"X-Test-Bypass": "true"})

    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert data["sources"][0]["id"] == "vercel-skills"


@pytest.mark.unit
def test_list_all_source_skills(mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_ALL_SKILLS
    mock_httpx_client.get.return_value = mock_response

    client = TestClient(app)
    response = client.get("/api/v1/skill-sources/skills?refresh=0&enabled_only=1", headers={"X-Test-Bypass": "true"})

    assert response.status_code == 200
    data = response.json()
    assert data["errors"] == []
    assert data["skills"][0]["source_id"] == "vercel-skills"


@pytest.mark.unit
def test_create_skill_source(mock_httpx_client):
    payload = {
        "id": "local",
        "name": "Local Skills",
        "repo_url": "owner/repo",
        "subdir": "skills",
        "ref": None,
        "enabled": True,
        "builtin": False,
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = payload
    mock_httpx_client.post.return_value = mock_response

    client = TestClient(app)
    response = client.post("/api/v1/skill-sources", json={"repo_url": "owner/repo"}, headers={"X-Test-Bypass": "true"})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "local"

