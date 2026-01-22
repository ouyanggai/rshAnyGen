"""Skills 管理 API"""
from fastapi import APIRouter, HTTPException, Body, Depends
from typing import List
from pydantic import BaseModel
import httpx

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from apps.gateway.models import SkillInfo, SkillListResponse
from apps.gateway.middleware.auth import require_auth, require_any_role

# 使用共享配置实例
config = ConfigLoader()
# 使用共享日志管理器
logger_manager = LogManager("gateway")
logger = logger_manager.get_logger()


class ToggleRequest(BaseModel):
    """Toggle 请求"""
    enabled: bool

router = APIRouter(prefix="/api/v1/skills", tags=["skills"], dependencies=[Depends(require_auth)])

# 从配置文件读取 Skills Registry URL
SKILLS_REGISTRY_URL = config.get(
    "services.skills_registry.url",
    "http://localhost:9303"
)

@router.get("")
async def list_skills() -> SkillListResponse:
    """获取所有 Skills 列表"""
    logger.info("Listing all skills from registry")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SKILLS_REGISTRY_URL}/api/v1/skills")
            if response.status_code != 200:
                logger.error(f"Failed to fetch skills: {response.status_code}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            
            data = response.json()
            registry_skills = data.get("skills", [])
            
            # Map registry skills to Gateway SkillInfo
            skills = []
            for s in registry_skills:
                skills.append(SkillInfo(
                    id=s["id"],
                    name=s.get("title") or s["id"],
                    description=s.get("description", ""),
                    enabled=s.get("enabled", True),
                    requires_consent=False, # Registry doesn't have this yet, default False
                    category=s.get("category")
                ))
            
            return SkillListResponse(skills=skills)
            
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")

@router.get("/{skill_id}")
async def get_skill(skill_id: str) -> SkillInfo:
    """获取指定 Skill 的详细信息"""
    logger.info(f"Getting skill: {skill_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SKILLS_REGISTRY_URL}/api/v1/skills/{skill_id}")
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
            if response.status_code != 200:
                logger.error(f"Failed to fetch skill {skill_id}: {response.status_code}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            
            s = response.json()
            
            return SkillInfo(
                id=s["id"],
                name=s.get("title") or s["id"],
                description=s.get("description", ""),
                enabled=s.get("enabled", True),
                requires_consent=False,
                category=s.get("category")
            )

    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")

@router.post("/{skill_id}/toggle")
async def toggle_skill(
    skill_id: str,
    request: ToggleRequest,
    _user=Depends(require_any_role(["admin"])),
) -> SkillInfo:
    """启用/禁用 Skill (暂未实现后端持久化)"""
    logger.info(f"Toggling skill {skill_id} to {request.enabled}")
    
    # 目前 Skills Registry API 没有 toggle 接口
    # 这里先获取 info，修改 enabled 返回，但不保存
    # TODO: 实现 Redis 状态存储或 Registry 更新接口
    
    skill = await get_skill(skill_id)
    skill.enabled = request.enabled
    return skill
