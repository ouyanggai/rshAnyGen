"""Skill 执行器单元测试"""
import pytest
from pathlib import Path
from services.skills_registry.executor import SkillExecutor, PythonFunctionExecutor
from services.skills_registry.loader import SkillLoader


class TestPythonFunctionExecutor:
    """Python 函数执行器测试"""

    def test_run_success(self, tmp_path):
        """测试成功执行"""
        # 创建测试 Skill
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # 创建 SKILL.md
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test_skill\nexecution_type: function\n---\n"
        )

        # 创建 api.py
        (skill_dir / "api.py").write_text(
            "def invoke(args, context):\n"
            "    return {'message': args.get('msg', 'hello')}\n"
        )

        # 执行
        skill_info = {
            "metadata": {"name": "test_skill", "execution_type": "function"},
            "api_file": skill_dir / "api.py"
        }

        import asyncio

        async def test_run():
            executor = PythonFunctionExecutor(config=None)
            result = await executor.run(skill_info, {"msg": "test"}, {})
            assert result == {"message": "test"}

        asyncio.run(test_run())

    def test_run_missing_api_file(self):
        """测试 API 文件不存在"""
        skill_info = {
            "metadata": {"name": "test_skill"},
            "api_file": Path("/nonexistent/api.py")
        }

        import asyncio

        async def test_run():
            executor = PythonFunctionExecutor(config=None)
            with pytest.raises(ValueError, match="API file not found"):
                await executor.run(skill_info, {}, {})

        asyncio.run(test_run())

    def test_run_missing_invoke_function(self, tmp_path):
        """测试缺少 invoke 函数"""
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()

        (skill_dir / "api.py").write_text("# no invoke function\n")

        skill_info = {
            "metadata": {"name": "bad_skill"},
            "api_file": skill_dir / "api.py"
        }

        import asyncio

        async def test_run():
            executor = PythonFunctionExecutor(config=None)
            with pytest.raises(ValueError, match="must have an 'invoke' function"):
                await executor.run(skill_info, {}, {})

        asyncio.run(test_run())


class TestSkillExecutor:
    """Skill 执行调度器测试"""

    def test_execute_success(self, tmp_path):
        """测试成功执行 Skill"""
        # 创建测试 Skill
        skill_dir = tmp_path / "test-executor-skill"
        skill_dir.mkdir()

        (skill_dir / "SKILL.md").write_text(
            "---\nname: executor_test\nexecution_type: function\n---\n"
        )

        (skill_dir / "api.py").write_text(
            "def invoke(args, context):\n"
            "    return {'result': args.get('value', 0) * 2}\n"
        )

        # 使用自定义 loader
        loader = SkillLoader(skills_dir=str(tmp_path))
        executor = SkillExecutor(loader=loader)

        import asyncio

        async def test_exec():
            result = await executor.execute("executor_test", {"value": 5})
            assert result["status"] == "success"
            assert result["result"] == {"result": 10}
            assert result["skill"] == "executor_test"
            assert result["executor"] == "function"
            assert result["execution_time_ms"] >= 0

        asyncio.run(test_exec())

    def test_execute_skill_not_found(self):
        """测试 Skill 不存在"""
        executor = SkillExecutor()

        import asyncio

        async def test_exec():
            result = await executor.execute("nonexistent", {})
            assert result["status"] == "error"
            assert "not found" in result["error"].lower()

        asyncio.run(test_exec())

    def test_execute_with_error(self, tmp_path):
        """测试执行出错"""
        skill_dir = tmp_path / "error-skill"
        skill_dir.mkdir()

        (skill_dir / "SKILL.md").write_text(
            "---\nname: error_skill\nexecution_type: function\n---\n"
        )

        (skill_dir / "api.py").write_text(
            "def invoke(args, context):\n"
            "    raise ValueError('Test error')\n"
        )

        loader = SkillLoader(skills_dir=str(tmp_path))
        executor = SkillExecutor(loader=loader)

        import asyncio

        async def test_exec():
            result = await executor.execute("error_skill", {})
            assert result["status"] == "error"
            assert "Test error" in result["error"]

        asyncio.run(test_exec())
