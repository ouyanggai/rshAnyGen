"""Skill 执行调度器"""
import time
from typing import Dict, Any, Optional
from pathlib import Path
import importlib.util
import sys

from .loader import SkillLoader


class MCPToolExecutor:
    """MCP 工具执行器（预留接口）"""

    def __init__(self, config):
        self.config = config

    async def run(self, skill_info: Dict[str, Any], args: dict, context: dict) -> Any:
        """执行 MCP 工具调用"""
        from apps.mcp_manager.manager import MCPManager

        metadata = skill_info.get("metadata", {}) or {}
        mcp_config = metadata.get("mcp", {}) or {}
        server_name = mcp_config.get("server") or metadata.get("mcp_server")
        tool_name = mcp_config.get("tool") or metadata.get("mcp_tool")

        if not server_name or not tool_name:
            raise ValueError("Missing MCP configuration in SKILL.md (mcp.server / mcp.tool)")

        manager = MCPManager()
        try:
            await manager.connect_server(server_name)
            result = await manager.call_tool(server_name, tool_name, args)
            return result
        finally:
            await manager.disconnect_all()


class HTTPAPIExecutor:
    """HTTP API 执行器（预留接口）"""

    def __init__(self, config):
        self.config = config

    async def run(self, skill_info: Dict[str, Any], args: dict, context: dict) -> Any:
        """执行 HTTP API 调用"""
        import httpx

        metadata = skill_info.get("metadata", {}) or {}
        http_config = metadata.get("http", {}) or {}

        method = (http_config.get("method") or "POST").upper()
        url = http_config.get("url")
        headers = http_config.get("headers") or {}
        timeout = http_config.get("timeout", 30000) / 1000.0

        if not url:
            raise ValueError("Missing HTTP configuration in SKILL.md (http.url)")

        async with httpx.AsyncClient(timeout=timeout) as client:
            if method in ("GET", "DELETE"):
                response = await client.request(method, url, params=args, headers=headers)
            else:
                response = await client.request(method, url, json=args, headers=headers)

            response.raise_for_status()
            try:
                return response.json()
            except Exception:
                return response.text


class PythonFunctionExecutor:
    """Python 函数执行器"""

    def __init__(self, config):
        self.config = config

    async def run(self, skill_info: Dict[str, Any], args: dict, context: dict) -> Any:
        """执行 Python 函数调用"""
        api_file = skill_info.get("api_file")
        if not api_file or not api_file.exists():
            raise ValueError(f"API file not found: {api_file}")

        # 动态加载模块
        spec = importlib.util.spec_from_file_location(
            f"skill_{skill_info['metadata']['name']}",
            api_file
        )
        if spec is None or spec.loader is None:
            raise ValueError(f"Cannot load module from {api_file}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        # 调用 invoke 函数
        if not hasattr(module, "invoke"):
            raise ValueError(f"Module {api_file} must have an 'invoke' function")

        invoke_func = getattr(module, "invoke")
        result = invoke_func(args, context)

        return result


class PromptExecutor:
    """Prompt/说明类 Skill 执行器（仅返回 SKILL.md 内容供 LLM 遵循）"""

    def __init__(self, config):
        self.config = config

    async def run(self, skill_info: Dict[str, Any], args: dict, context: dict) -> Any:
        skill_md: Optional[Path] = skill_info.get("skill_md")
        if not skill_md or not skill_md.exists():
            # 兼容旧数据结构
            skill_path = skill_info.get("path")
            if skill_path:
                candidate = Path(skill_path) / "SKILL.md"
                if candidate.exists():
                    skill_md = candidate

        if not skill_md or not skill_md.exists():
            raise ValueError("SKILL.md not found for prompt skill")

        return {
            "instructions_markdown": skill_md.read_text(encoding="utf-8"),
            "args": args or {},
            "context": context or {},
        }


class SkillExecutor:
    """Skill 执行调度器"""

    def __init__(self, loader: Optional[SkillLoader] = None):
        """初始化执行器

        Args:
            loader: Skill 加载器实例，如果为 None 则创建新实例
        """
        self.loader = loader or SkillLoader()

    async def execute(
        self,
        skill_name: str,
        args: dict,
        context: Optional[dict] = None
    ) -> Dict[str, Any]:
        """执行 Skill

        Args:
            skill_name: Skill 名称
            args: Skill 参数
            context: 执行上下文（可选）

        Returns:
            {
                "status": "success" | "error",
                "result": 执行结果,
                "execution_time_ms": 执行耗时
            }
        """
        start_time = time.time()
        context = context or {}

        try:
            # 加载 Skill 信息
            skills = self.loader.load_all_skills()
            skill_info = skills.get(skill_name)

            if not skill_info:
                raise ValueError(f"Skill not found: {skill_name}")

            # 获取执行类型
            execution_type = (skill_info.get("metadata", {}) or {}).get("execution_type")
            if not execution_type:
                api_file = skill_info.get("api_file")
                if api_file and api_file.exists():
                    execution_type = "function"
                else:
                    execution_type = "prompt"

            # 创建对应的执行器
            if execution_type == "function":
                executor = PythonFunctionExecutor(config=None)
            elif execution_type == "mcp_tool":
                executor = MCPToolExecutor(config=None)
            elif execution_type == "http_api":
                executor = HTTPAPIExecutor(config=None)
            elif execution_type == "prompt":
                executor = PromptExecutor(config=None)
            else:
                raise ValueError(f"Unsupported execution type: {execution_type}")

            # 执行 Skill
            result = await executor.run(skill_info, args, context)

            return {
                "status": "success",
                "result": result,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "skill": skill_name,
                "executor": execution_type
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "skill": skill_name
            }
