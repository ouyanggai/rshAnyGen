"""Git/repo helpers for skills installation and indexing."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import yaml


def parse_skill_frontmatter(skill_md_path: Path) -> dict:
    content = skill_md_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md 缺少 YAML frontmatter（--- ... ---）")
    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("SKILL.md frontmatter 解析失败")
    return data


def ensure_execution_type(skill_dir: Path) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return
    content = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n?", content, re.DOTALL)
    if not match:
        return

    frontmatter = yaml.safe_load(match.group(1)) or {}
    if not isinstance(frontmatter, dict):
        return
    if "execution_type" in frontmatter:
        return

    exec_type = "function" if (skill_dir / "api.py").exists() else "prompt"

    fm_text = match.group(1).rstrip("\n")
    fm_text = fm_text + f"\nexecution_type: {exec_type}\n"
    new_content = f"---\n{fm_text}---\n" + content[match.end() :]
    skill_md.write_text(new_content, encoding="utf-8")


def infer_execution_type(metadata: dict, skill_dir: Optional[Path] = None) -> str:
    execution_type = (metadata or {}).get("execution_type")
    if execution_type:
        return str(execution_type)
    if skill_dir and (skill_dir / "api.py").exists():
        return "function"
    return "prompt"


def git_clone(repo_url: str, dest_dir: Path, ref: Optional[str]) -> None:
    dest_dir.parent.mkdir(parents=True, exist_ok=True)

    def _is_ref_error(detail: str) -> bool:
        lowered = (detail or "").lower()
        return ("remote branch" in lowered) or ("couldn't find remote ref" in lowered)

    def _attempt_clone(maybe_ref: Optional[str]) -> Optional[str]:
        base_cmd = ["git", "clone", "--depth", "1"]
        if maybe_ref:
            base_cmd += ["--branch", maybe_ref, "--single-branch"]

        candidates = [
            base_cmd + ["--filter=blob:none", repo_url, str(dest_dir)],
            base_cmd + [repo_url, str(dest_dir)],
        ]

        last_detail: Optional[str] = None
        for cmd in candidates:
            if dest_dir.exists():
                shutil.rmtree(dest_dir, ignore_errors=True)
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
                return None
            except subprocess.TimeoutExpired:
                last_detail = "git clone 超时"
            except subprocess.CalledProcessError as e:
                last_detail = (e.stderr or e.stdout or str(e)).strip()

        return last_detail or "git clone 失败"

    detail = _attempt_clone(ref)
    if detail is None:
        return

    if ref and _is_ref_error(detail):
        detail2 = _attempt_clone(None)
        if detail2 is None:
            return
        detail = detail2

    raise ValueError(f"git clone 失败: {detail}")

