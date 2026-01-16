"""Skill 加载器测试"""
import pytest
from pathlib import Path


@pytest.mark.unit
def test_load_all_skills():
    """测试：加载所有 Skills"""
    from services.skills_registry.loader import SkillLoader

    # 使用项目根目录的绝对路径
    skills_dir = Path(__file__).parent.parent.parent.parent / "services" / "skills_registry" / "storage" / "skills"
    loader = SkillLoader(str(skills_dir))
    skills = loader.load_all_skills()

    assert "web_search" in skills
    assert skills["web_search"]["metadata"]["title"] == "Web Search"


@pytest.mark.unit
def test_parse_skill_md():
    """测试：解析 SKILL.md"""
    from services.skills_registry.loader import SkillLoader

    # 使用项目根目录的绝对路径
    skills_dir = Path(__file__).parent.parent.parent.parent / "services" / "skills_registry" / "storage" / "skills"
    loader = SkillLoader(str(skills_dir))
    skills = loader.load_all_skills()

    skill_info = skills["web_search"]
    assert skill_info["metadata"]["category"] == "search"
    assert skill_info["metadata"]["version"] == "1.0.0"
    assert skill_info["metadata"]["description"] == "Search the web for current information"


@pytest.mark.unit
def test_get_skill_api():
    """测试：获取 Skill API 模块"""
    from services.skills_registry.loader import SkillLoader

    # 使用项目根目录的绝对路径
    skills_dir = Path(__file__).parent.parent.parent.parent / "services" / "skills_registry" / "storage" / "skills"
    loader = SkillLoader(str(skills_dir))

    # 测试获取存在的 Skill
    api_module = loader.get_skill_api("web_search")
    assert api_module is not None
    assert hasattr(api_module, "invoke")

    # 测试 invoke 函数调用
    result = api_module.invoke(
        {"query": "test query", "top_n": 5},
        {"session_id": "test_session"}
    )
    assert result["status"] == "success"
    assert result["result"]["query"] == "test query"
    assert result["result"]["top_n"] == 5


@pytest.mark.unit
def test_get_skill_api_not_found():
    """测试：获取不存在的 Skill"""
    from services.skills_registry.loader import SkillLoader

    # 使用项目根目录的绝对路径
    skills_dir = Path(__file__).parent.parent.parent.parent / "services" / "skills_registry" / "storage" / "skills"
    loader = SkillLoader(str(skills_dir))

    with pytest.raises(ValueError, match="Skill not found"):
        loader.get_skill_api("non_existent_skill")


@pytest.mark.unit
def test_load_skills_empty_dir():
    """测试：加载空目录"""
    from services.skills_registry.loader import SkillLoader

    loader = SkillLoader("non_existent_dir")
    skills = loader.load_all_skills()

    assert skills == {}
