"""Skill 加载器 - 遵循 Claude Skills 协议"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
import importlib.util
import sys


class SkillLoader:
    """Claude Skills 加载器"""

    def __init__(self, skills_dirs: Optional[List[str]] = None):
        # 技能目录来源（按优先级从低到高加载；后加载会覆盖前加载的同名 skill）
        #
        # 1) 内置技能：services/skills_registry/storage/skills
        # 2) 用户技能：<repo-root>/storage/skills
        #
        # 说明：使用 metadata.name 作为 skill_id，因此目录名可以是 web-search / web_search。
        if skills_dirs is not None:
            self.skills_dirs = [Path(p) for p in skills_dirs]
        else:
            here = Path(__file__).resolve()
            builtin_dir = here.parent / "storage" / "skills"
            # services/skills_registry/loader.py -> services/skills_registry -> services -> repo-root
            repo_root = here.parents[2]
            user_dir = repo_root / "storage" / "skills"

            # 去重保持顺序
            seen = set()
            dirs: List[Path] = []
            for d in [builtin_dir, user_dir]:
                key = str(d)
                if key in seen:
                    continue
                seen.add(key)
                dirs.append(d)

            self.skills_dirs = dirs

    def load_all_skills(self) -> Dict[str, Dict[str, Any]]:
        """加载所有 Skills"""
        skills = {}

        for skills_dir in self.skills_dirs:
            if not skills_dir.exists():
                continue

            for skill_path in skills_dir.iterdir():
                if not skill_path.is_dir():
                    continue

                skill_md = skill_path / "SKILL.md"
                if not skill_md.exists():
                    continue

                try:
                    skill_info = self._parse_skill_md(skill_md)
                except Exception:
                    # 单个 skill 解析失败不影响其他 skill
                    continue

                name = (skill_info.get("name") or "").strip()
                if not name:
                    continue

                skills[name] = {
                    "path": str(skill_path),
                    "metadata": skill_info,
                    "skill_md": skill_md,
                    "api_file": skill_path / "api.py",
                }

        return skills

    def _parse_skill_md(self, md_file: Path) -> Dict[str, Any]:
        """解析 SKILL.md 文件"""
        content = md_file.read_text(encoding='utf-8')

        # 提取 frontmatter（--- 之间的 YAML）
        frontmatter_match = re.match(
            r'^---\n(.*?)\n---',
            content,
            re.DOTALL
        )

        if frontmatter_match:
            metadata = yaml.safe_load(frontmatter_match.group(1))
            return metadata

        raise ValueError(f"Invalid SKILL.md: {md_file}")

    def get_skill_api(self, skill_name: str):
        """动态加载 Skill 的 API 模块"""
        skill_info = self.load_all_skills().get(skill_name)
        if not skill_info:
            raise ValueError(f"Skill not found: {skill_name}")

        api_file = skill_info["api_file"]
        if not api_file.exists():
            return None

        spec = importlib.util.spec_from_file_location(
            f"skill_{skill_name}",
            api_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module
