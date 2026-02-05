"""Git/repo helpers for skills installation and indexing."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

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
    git_clone_with_options(repo_url, dest_dir, ref, env=None, timeout_seconds=180, on_output=None)


def git_clone_with_options(
    repo_url: str,
    dest_dir: Path,
    ref: Optional[str],
    *,
    env: Optional[dict[str, str]],
    timeout_seconds: int,
    on_output: Optional[Callable[[str], None]],
) -> None:
    dest_dir.parent.mkdir(parents=True, exist_ok=True)

    def _is_ref_error(detail: str) -> bool:
        lowered = (detail or "").lower()
        return ("remote branch" in lowered) or ("couldn't find remote ref" in lowered)

    def _stream_process(cmd: list[str]) -> Optional[str]:
        env_map = dict(os.environ)
        if env:
            env_map.update({k: str(v) for k, v in env.items() if v is not None})

        # Avoid hanging on credentials prompt
        env_map.setdefault("GIT_TERMINAL_PROMPT", "0")

        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env_map,
        )

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        def _reader(stream, sink: list[str], prefix: str):
            try:
                for line in iter(stream.readline, ""):
                    # git progress might use \r; normalize a bit
                    line = line.replace("\r", "").rstrip("\n")
                    if not line:
                        continue
                    sink.append(line)
                    if on_output:
                        on_output(f"{prefix}{line}")
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        t_out = threading.Thread(target=_reader, args=(proc.stdout, stdout_lines, ""), daemon=True)
        t_err = threading.Thread(target=_reader, args=(proc.stderr, stderr_lines, ""), daemon=True)
        t_out.start()
        t_err.start()

        timed_out = False
        try:
            proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                proc.kill()
            except Exception:
                pass
            proc.wait(timeout=10)

        t_out.join(timeout=2)
        t_err.join(timeout=2)

        if timed_out:
            return "git clone 超时"
        if proc.returncode == 0:
            return None

        detail_lines = (stderr_lines or stdout_lines)[-80:]
        detail = "\n".join(detail_lines).strip()
        return detail or f"git clone 失败 (code={proc.returncode})"

    def _run_capture(cmd: list[str]) -> Optional[str]:
        env_map = dict(os.environ)
        if env:
            env_map.update({k: str(v) for k, v in env.items() if v is not None})
        env_map.setdefault("GIT_TERMINAL_PROMPT", "0")

        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)

        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env_map,
            )
            return None
        except subprocess.TimeoutExpired:
            return "git clone 超时"
        except subprocess.CalledProcessError as e:
            return (e.stderr or e.stdout or str(e)).strip() or "git clone 失败"

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
            if on_output:
                on_output("$ " + " ".join(cmd))
            if on_output:
                # Force progress output to stderr for streaming.
                cmd2 = cmd[:]
                if "--progress" not in cmd2:
                    cmd2.insert(2, "--progress")
                last_detail = _stream_process(cmd2)
            else:
                last_detail = _run_capture(cmd)
            if last_detail is None:
                return None

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
