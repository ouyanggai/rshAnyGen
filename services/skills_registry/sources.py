"""Skill sources management (git repos containing multiple skills)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass(frozen=True)
class SkillSource:
    id: str
    name: str
    repo_url: str
    subdir: str = "skills"
    ref: Optional[str] = None
    enabled: bool = True
    builtin: bool = False
    description: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "repo_url": self.repo_url,
            "subdir": self.subdir,
            "ref": self.ref,
            "enabled": bool(self.enabled),
            "builtin": bool(self.builtin),
            "description": self.description,
        }


# Curated defaults (big tech/community first). These are NOT persisted to git.
DEFAULT_SOURCES: list[SkillSource] = [
    SkillSource(
        id="openai-skills",
        name="OpenAI Skills",
        repo_url="https://github.com/openai/skills.git",
        subdir="skills",
        ref=None,
        builtin=True,
        description="OpenAI 官方技能集合（含 curated/experimental 等子目录）",
    ),
    SkillSource(
        id="anthropics-skills",
        name="Anthropic Skills",
        repo_url="https://github.com/anthropics/skills.git",
        subdir="skills",
        ref=None,
        builtin=True,
        description="Anthropic 官方技能集合",
    ),
    SkillSource(
        id="vercel-agent-skills",
        name="Vercel Agent Skills",
        repo_url="https://github.com/vercel-labs/agent-skills.git",
        subdir="skills",
        ref=None,
        builtin=True,
        description="Vercel Labs 出品的 agent skills",
    ),
    SkillSource(
        id="vercel-skills",
        name="Vercel Labs Skills",
        repo_url="https://github.com/vercel-labs/skills.git",
        subdir="skills",
        ref=None,
        builtin=True,
        description="Vercel Labs 出品的 skills（你提到的示例源）",
    ),
    SkillSource(
        id="huggingface-skills",
        name="Hugging Face Skills",
        repo_url="https://github.com/huggingface/skills.git",
        subdir="skills",
        ref=None,
        builtin=True,
        description="Hugging Face 官方 skills 仓库",
    ),
]


def _safe_slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "source"


def _default_source_id_for_repo(repo_url: str, subdir: str) -> str:
    raw = (repo_url or "").strip()
    # Common GitHub formats
    m = re.search(r"github\.com[:/]+([^/]+)/([^/#?]+)", raw)
    if m:
        owner = _safe_slugify(m.group(1))
        repo = _safe_slugify(m.group(2).removesuffix(".git"))
        base = f"{owner}-{repo}"
    else:
        base = _safe_slugify(Path(raw).name.removesuffix(".git"))

    sd = (subdir or "skills").strip().strip("/")
    if sd and sd not in ("skills", "."):
        base = f"{base}-{_safe_slugify(sd)}"

    return base


def normalize_repo_url(repo_url: str) -> str:
    repo_url = (repo_url or "").strip()
    if not repo_url:
        raise ValueError("repo_url 不能为空")

    # owner/repo -> https://github.com/owner/repo.git
    if "://" not in repo_url and repo_url.count("/") == 1 and not repo_url.startswith("git@"):
        return f"https://github.com/{repo_url}.git"

    # https://github.com/owner/repo -> add .git (git accepts without too, but be consistent)
    if repo_url.startswith("https://github.com/") and not repo_url.endswith(".git"):
        return repo_url + ".git"

    return repo_url


class SkillSourcesStore:
    """Persist user-added sources and overrides for builtin defaults."""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "user_sources": [], "disabled_default_source_ids": []}
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            return {"version": 1, "user_sources": [], "disabled_default_source_ids": []}
        data.setdefault("version", 1)
        data.setdefault("user_sources", [])
        data.setdefault("disabled_default_source_ids", [])
        if not isinstance(data["user_sources"], list):
            data["user_sources"] = []
        if not isinstance(data["disabled_default_source_ids"], list):
            data["disabled_default_source_ids"] = []
        return data

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        self.path.write_text(content, encoding="utf-8")


class SkillSourcesService:
    def __init__(self, store: SkillSourcesStore, defaults: list[SkillSource]):
        self._store = store
        self._defaults = defaults

    def list_sources(self) -> list[SkillSource]:
        cfg = self._store.load()
        disabled_defaults = {str(x) for x in (cfg.get("disabled_default_source_ids") or [])}

        sources: list[SkillSource] = []
        for s in self._defaults:
            sources.append(
                SkillSource(
                    id=s.id,
                    name=s.name,
                    repo_url=s.repo_url,
                    subdir=s.subdir,
                    ref=s.ref,
                    enabled=s.id not in disabled_defaults,
                    builtin=True,
                    description=s.description,
                )
            )

        for raw in cfg.get("user_sources") or []:
            if not isinstance(raw, dict):
                continue
            sid = str(raw.get("id") or "").strip()
            if not sid:
                continue
            sources.append(
                SkillSource(
                    id=sid,
                    name=str(raw.get("name") or sid),
                    repo_url=str(raw.get("repo_url") or ""),
                    subdir=str(raw.get("subdir") or "skills"),
                    ref=(str(raw.get("ref")).strip() if raw.get("ref") else None),
                    enabled=bool(raw.get("enabled", True)),
                    builtin=False,
                    description=(str(raw.get("description")).strip() if raw.get("description") else None),
                )
            )

        # Keep stable ordering: defaults first (already), then user sources by name/id
        return sources

    def get_source(self, source_id: str) -> SkillSource:
        source_id = str(source_id or "").strip()
        for s in self.list_sources():
            if s.id == source_id:
                return s
        raise KeyError(f"Source not found: {source_id}")

    def add_user_source(
        self,
        *,
        repo_url: str,
        name: Optional[str] = None,
        subdir: str = "skills",
        ref: Optional[str] = None,
        source_id: Optional[str] = None,
        enabled: bool = True,
        description: Optional[str] = None,
    ) -> SkillSource:
        repo_url_norm = normalize_repo_url(repo_url)
        subdir = (subdir or "skills").strip().strip("/") or "skills"
        source_id = (source_id or "").strip() or _default_source_id_for_repo(repo_url_norm, subdir)

        # Ensure no collisions with existing sources
        existing_ids = {s.id for s in self.list_sources()}
        if source_id in existing_ids:
            raise ValueError(f"source_id 已存在: {source_id}")

        cfg = self._store.load()
        user_sources = cfg.get("user_sources") or []
        if not isinstance(user_sources, list):
            user_sources = []

        src = SkillSource(
            id=source_id,
            name=(name or source_id).strip(),
            repo_url=repo_url_norm,
            subdir=subdir,
            ref=(ref.strip() if ref else None),
            enabled=bool(enabled),
            builtin=False,
            description=(description.strip() if description else None),
        )

        user_sources.append(
            {
                "id": src.id,
                "name": src.name,
                "repo_url": src.repo_url,
                "subdir": src.subdir,
                "ref": src.ref,
                "enabled": src.enabled,
                "description": src.description,
            }
        )
        cfg["user_sources"] = user_sources
        self._store.save(cfg)
        return src

    def set_enabled(self, source_id: str, enabled: bool) -> SkillSource:
        enabled = bool(enabled)
        source_id = str(source_id or "").strip()
        if not source_id:
            raise ValueError("source_id 不能为空")

        # builtin -> update disabled_default_source_ids
        defaults = {s.id: s for s in self._defaults}
        cfg = self._store.load()

        if source_id in defaults:
            disabled = {str(x) for x in (cfg.get("disabled_default_source_ids") or [])}
            if enabled:
                disabled.discard(source_id)
            else:
                disabled.add(source_id)
            cfg["disabled_default_source_ids"] = sorted(disabled)
            self._store.save(cfg)
            return SkillSource(
                id=defaults[source_id].id,
                name=defaults[source_id].name,
                repo_url=defaults[source_id].repo_url,
                subdir=defaults[source_id].subdir,
                ref=defaults[source_id].ref,
                enabled=enabled,
                builtin=True,
                description=defaults[source_id].description,
            )

        # user source -> update entry
        user_sources = cfg.get("user_sources") or []
        if not isinstance(user_sources, list):
            user_sources = []

        updated: Optional[dict[str, Any]] = None
        for raw in user_sources:
            if not isinstance(raw, dict):
                continue
            if str(raw.get("id") or "").strip() == source_id:
                raw["enabled"] = enabled
                updated = raw
                break
        if updated is None:
            raise KeyError(f"Source not found: {source_id}")

        cfg["user_sources"] = user_sources
        self._store.save(cfg)
        return SkillSource(
            id=source_id,
            name=str(updated.get("name") or source_id),
            repo_url=str(updated.get("repo_url") or ""),
            subdir=str(updated.get("subdir") or "skills"),
            ref=(str(updated.get("ref")).strip() if updated.get("ref") else None),
            enabled=enabled,
            builtin=False,
            description=(str(updated.get("description")).strip() if updated.get("description") else None),
        )

    def delete_source(self, source_id: str) -> None:
        source_id = str(source_id or "").strip()
        if not source_id:
            raise ValueError("source_id 不能为空")

        defaults = {s.id for s in self._defaults}
        cfg = self._store.load()
        if source_id in defaults:
            # For builtin sources, treat delete as disable.
            disabled = {str(x) for x in (cfg.get("disabled_default_source_ids") or [])}
            disabled.add(source_id)
            cfg["disabled_default_source_ids"] = sorted(disabled)
            self._store.save(cfg)
            return

        user_sources = cfg.get("user_sources") or []
        if not isinstance(user_sources, list):
            user_sources = []
        new_sources = []
        removed = False
        for raw in user_sources:
            if not isinstance(raw, dict):
                continue
            if str(raw.get("id") or "").strip() == source_id:
                removed = True
                continue
            new_sources.append(raw)
        if not removed:
            raise KeyError(f"Source not found: {source_id}")

        cfg["user_sources"] = new_sources
        self._store.save(cfg)

