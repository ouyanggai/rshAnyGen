"""Skills 管理 API"""
from fastapi import APIRouter, HTTPException, Body
from typing import List
from pydantic import BaseModel

from apps.shared.logger import LogManager
from apps.gateway.models import SkillInfo, SkillListResponse

# 使用共享日志管理器
logger_manager = LogManager("gateway")
logger = logger_manager.get_logger()


class ToggleRequest(BaseModel):
    """Toggle 请求"""
    enabled: bool

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])

# 模拟技能数据（TODO: 从 Skills Registry 服务获取）
MOCK_SKILLS = [
    {
        "id": "web_search",
        "name": "网页搜索",
        "description": "在百度搜索引擎中搜索关键词并获取网页内容",
        "enabled": True,
        "requires_consent": True,
        "category": "search"
    },
    {
        "id": "knowledge_query",
        "name": "知识库查询",
        "description": "从内部知识库检索相关文档",
        "enabled": True,
        "requires_consent": False,
        "category": "knowledge"
    },
    {
        "id": "code_interpreter",
        "name": "代码执行",
        "description": "安全地执行 Python 代码片段",
        "enabled": False,
        "requires_consent": True,
        "category": "tools"
    }
]

@router.get("")
async def list_skills() -> SkillListResponse:
    """获取所有 Skills 列表"""
    logger.info("Listing all skills")
    skills = [SkillInfo(**skill) for skill in MOCK_SKILLS]
    return SkillListResponse(skills=skills)

@router.get("/{skill_id}")
async def get_skill(skill_id: str) -> SkillInfo:
    """获取指定 Skill 的详细信息"""
    logger.info(f"Getting skill: {skill_id}")

    for skill in MOCK_SKILLS:
        if skill["id"] == skill_id:
            return SkillInfo(**skill)

    raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

@router.post("/{skill_id}/toggle")
async def toggle_skill(skill_id: str, request: ToggleRequest) -> SkillInfo:
    """启用/禁用 Skill"""
    logger.info(f"Toggling skill {skill_id} to {request.enabled}")

    for skill in MOCK_SKILLS:
        if skill["id"] == skill_id:
            skill["enabled"] = request.enabled
            return SkillInfo(**skill)

    raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
