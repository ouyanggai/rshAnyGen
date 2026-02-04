"""Remote (git) skill indexing utilities."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .git_utils import git_clone, infer_execution_type, parse_skill_frontmatter
from .sources import SkillSource, normalize_repo_url


def list_skills_in_source(source: SkillSource) -> list[dict]:
    repo_url = normalize_repo_url(source.repo_url)
    subdir = (source.subdir or "skills").strip().strip("/") or "skills"

    with tempfile.TemporaryDirectory(prefix="skills_source_index_") as tmp:
        tmp_repo = Path(tmp) / "repo"
        git_clone(repo_url, tmp_repo, source.ref)

        root = (tmp_repo / subdir).resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"未找到 skills 子目录: {subdir}")

        items: list[dict] = []
        for skill_md in root.rglob("SKILL.md"):
            if not skill_md.is_file():
                continue

            skill_dir = skill_md.parent
            rel = skill_dir.relative_to(root)
            slug = rel.as_posix()
            if slug == ".":
                slug = "."

            try:
                metadata = parse_skill_frontmatter(skill_md)
            except Exception:
                # 单个 skill 解析失败不影响其他 skill
                continue

            skill_id = str(metadata.get("name") or "").strip()
            if not skill_id:
                continue

            items.append(
                {
                    "slug": slug,
                    "id": skill_id,
                    "title": metadata.get("title"),
                    "description": metadata.get("description"),
                    "category": metadata.get("category"),
                    "version": metadata.get("version"),
                    "execution_type": infer_execution_type(metadata, skill_dir),
                }
            )

        items.sort(key=lambda x: (str(x.get("id") or ""), str(x.get("slug") or "")))
        return items

