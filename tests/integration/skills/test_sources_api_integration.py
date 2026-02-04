"""Skill Sources API integration tests (offline, using a local git repo)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import services.skills_registry.api.main as main
from services.skills_registry.executor import SkillExecutor
from services.skills_registry.loader import SkillLoader
from services.skills_registry.sources import SkillSourcesService, SkillSourcesStore


@pytest.fixture
def local_skills_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "skills_repo"
    (repo / "skills" / "alpha-skill").mkdir(parents=True, exist_ok=True)
    (repo / "skills" / "alpha-skill" / "SKILL.md").write_text(
        "---\n"
        "name: alpha-skill\n"
        "title: Alpha Skill\n"
        "description: Alpha skill for testing.\n"
        "category: tools\n"
        "---\n"
        "\n"
        "Alpha.\n",
        encoding="utf-8",
    )
    (repo / "skills" / "alpha-skill" / "api.py").write_text(
        "def run(params, context):\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )

    (repo / "skills" / ".curated" / "beta-skill").mkdir(parents=True, exist_ok=True)
    (repo / "skills" / ".curated" / "beta-skill" / "SKILL.md").write_text(
        "---\n"
        "name: beta-skill\n"
        "title: Beta Skill\n"
        "description: Beta skill for testing.\n"
        "category: tools\n"
        "---\n"
        "\n"
        "Beta.\n",
        encoding="utf-8",
    )

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True, text=True)
    return repo


@pytest.fixture
def isolated_sources_and_dirs(monkeypatch, tmp_path: Path):
    # Patch sources config to a temp file and avoid builtin defaults that require network.
    store = SkillSourcesStore(tmp_path / "skill_sources.yaml")
    svc = SkillSourcesService(store=store, defaults=[])
    monkeypatch.setattr(main, "sources_service", svc)

    # Patch install dirs to temp and rewire loader/executor to include temp user skills.
    user_skills_dir = tmp_path / "user_skills"
    deleted_dir = tmp_path / "deleted"
    monkeypatch.setattr(main, "USER_SKILLS_DIR", user_skills_dir)
    monkeypatch.setattr(main, "DELETED_SKILLS_DIR", deleted_dir)

    builtin_dir = Path(main.__file__).resolve().parents[1] / "storage" / "skills"
    loader = SkillLoader(skills_dirs=[str(builtin_dir), str(user_skills_dir)])
    monkeypatch.setattr(main, "loader", loader)
    monkeypatch.setattr(main, "executor", SkillExecutor(loader=loader))

    return {"sources": svc, "user_skills_dir": user_skills_dir}


@pytest.mark.integration
class TestSkillSourcesAPI:
    def test_sources_workflow_offline(self, isolated_sources_and_dirs, local_skills_repo: Path):
        client = TestClient(main.app)

        # Create source
        res = client.post(
            "/api/v1/skill-sources",
            json={"repo_url": str(local_skills_repo), "subdir": "skills"},
        )
        assert res.status_code == 200
        source = res.json()
        source_id = source["id"]

        # List sources contains it
        res = client.get("/api/v1/skill-sources")
        assert res.status_code == 200
        ids = [s["id"] for s in res.json().get("sources", [])]
        assert source_id in ids

        # Index skills (first time should be uncached)
        res = client.get(f"/api/v1/skill-sources/{source_id}/skills")
        assert res.status_code == 200
        data = res.json()
        assert data["cached"] is False
        slugs = {s["slug"] for s in data.get("skills", [])}
        assert "alpha-skill" in slugs
        assert ".curated/beta-skill" in slugs

        # Index skills again (should be cached)
        res = client.get(f"/api/v1/skill-sources/{source_id}/skills")
        assert res.status_code == 200
        assert res.json()["cached"] is True

        # Aggregate all sources (only this one)
        res = client.get("/api/v1/skill-sources/skills")
        assert res.status_code == 200
        payload = res.json()
        assert payload.get("errors") == []
        assert any(s.get("source_id") == source_id for s in payload.get("skills", []))

        # Install from source
        res = client.post(
            f"/api/v1/skill-sources/{source_id}/install",
            json={"slug": "alpha-skill", "overwrite": False},
        )
        assert res.status_code == 200
        installed = res.json()
        assert installed["id"] == "alpha-skill"

        # Now remote list marks it as installed
        res = client.get(f"/api/v1/skill-sources/{source_id}/skills")
        skills = {s["id"]: s for s in res.json().get("skills", [])}
        assert skills["alpha-skill"]["installed"] is True

        # Disable source and verify blocked
        res = client.post(f"/api/v1/skill-sources/{source_id}/toggle", json={"enabled": False})
        assert res.status_code == 200
        res = client.get(f"/api/v1/skill-sources/{source_id}/skills")
        assert res.status_code == 400

        # Delete source
        res = client.delete(f"/api/v1/skill-sources/{source_id}")
        assert res.status_code == 200

