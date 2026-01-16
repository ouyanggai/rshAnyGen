"""Skill 加载器 - 遵循 Claude Skills 协议"""
import re
from pathlib import Path
from typing import List, Dict, Any
import yaml
import importlib.util
import sys


class SkillLoader:
    """Claude Skills 加载器"""

    def __init__(self, skills_dir: str = "storage/skills"):
        self.skills_dir = Path(skills_dir)

    def load_all_skills(self) -> Dict[str, Dict[str, Any]]:
        """加载所有 Skills"""
        skills = {}

        if not self.skills_dir.exists():
            return skills

        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir():
                skill_md = skill_path / "SKILL.md"
                if skill_md.exists():
                    skill_info = self._parse_skill_md(skill_md)
                    skills[skill_info["name"]] = {
                        "path": str(skill_path),
                        "metadata": skill_info,
                        "api_file": skill_path / "api.py"
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
