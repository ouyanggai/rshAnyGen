"""Skills 管理 API"""
from fastapi import APIRouter, HTTPException, Body, Depends
from typing import List, Optional
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


class InstallRequest(BaseModel):
    repo_url: str
    skill: str
    subdir: str = "skills"
    ref: Optional[str] = None
    overwrite: bool = False

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
        # trust_env=False：避免本机代理环境变量影响本地服务互调
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
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
                    category=s.get("category"),
                    version=s.get("version"),
                    execution_type=s.get("execution_type"),
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
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
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
                category=s.get("category"),
                version=s.get("version"),
                execution_type=s.get("execution_type"),
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
    """启用/禁用 Skill（持久化到 Skills Registry）"""
    logger.info(f"Toggling skill {skill_id} to {request.enabled}")

    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            resp = await client.post(
                f"{SKILLS_REGISTRY_URL}/api/v1/skills/{skill_id}/toggle",
                json={"enabled": request.enabled},
            )
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
            if resp.status_code != 200:
                logger.error(f"Failed to toggle skill {skill_id}: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")

            s = resp.json()
            return SkillInfo(
                id=s["id"],
                name=s.get("title") or s["id"],
                description=s.get("description", ""),
                enabled=s.get("enabled", True),
                requires_consent=False,
                category=s.get("category"),
                version=s.get("version"),
                execution_type=s.get("execution_type"),
            )
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.post("/install")
async def install_skill(
    request: InstallRequest,
    _user=Depends(require_any_role(["admin"])),
) -> SkillInfo:
    """一键安装 Skill（从 Git 仓库拉取到 storage/skills）"""
    logger.info(f"Installing skill {request.skill} from {request.repo_url}")
    try:
        async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
            resp = await client.post(
                f"{SKILLS_REGISTRY_URL}/api/v1/skills/install",
                json=request.model_dump(),
            )
            if resp.status_code == 400:
                raise HTTPException(status_code=400, detail=resp.json().get("detail") if resp.headers.get("content-type","").startswith("application/json") else resp.text)
            if resp.status_code != 200:
                logger.error(f"Failed to install skill: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")

            s = resp.json()
            return SkillInfo(
                id=s["id"],
                name=s.get("title") or s["id"],
                description=s.get("description", ""),
                enabled=s.get("enabled", True),
                requires_consent=False,
                category=s.get("category"),
                version=s.get("version"),
                execution_type=s.get("execution_type"),
            )
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.post("/install-async")
async def install_skill_async(
    request: InstallRequest,
    _user=Depends(require_any_role(["admin"])),
):
    """异步安装 Skill（返回 job_id，前端轮询获取进度）"""
    logger.info(f"Installing skill async {request.skill} from {request.repo_url}")
    try:
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            resp = await client.post(
                f"{SKILLS_REGISTRY_URL}/api/v1/skills/install-async",
                json=request.model_dump(),
            )
            if resp.status_code == 400:
                raise HTTPException(
                    status_code=400,
                    detail=resp.json().get("detail") if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
                )
            if resp.status_code != 200:
                logger.error(f"Failed to start install job: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.get("/install-jobs/{job_id}")
async def get_install_job(
    job_id: str,
    tail: int = 200,
    _user=Depends(require_any_role(["admin"])),
):
    """获取安装 Job 状态与日志"""
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            resp = await client.get(
                f"{SKILLS_REGISTRY_URL}/api/v1/skills/install-jobs/{job_id}",
                params={"tail": tail},
            )
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Install job not found")
            if resp.status_code != 200:
                logger.error(f"Failed to get install job: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    _user=Depends(require_any_role(["admin"])),
):
    """卸载 Skill（仅用户 skills）"""
    logger.info(f"Deleting skill: {skill_id}")
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            resp = await client.delete(f"{SKILLS_REGISTRY_URL}/api/v1/skills/{skill_id}")
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
            if resp.status_code == 403:
                raise HTTPException(status_code=403, detail="Built-in skills cannot be deleted")
            if resp.status_code != 200:
                logger.error(f"Failed to delete skill {skill_id}: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")
