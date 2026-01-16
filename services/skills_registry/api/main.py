"""Skills Registry API 入口"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..loader import SkillLoader
from ..executor import SkillExecutor


# 创建 FastAPI 应用
app = FastAPI(
    title="Skills Registry API",
    description="Claude Skills 协议实现的 REST API",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
loader = SkillLoader()
executor = SkillExecutor(loader=loader)


# 请求/响应模型
class ExecutionRequest(BaseModel):
    """Skill 执行请求"""
    params: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class SkillInfo(BaseModel):
    """Skill 信息"""
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    enabled: bool = True
    execution_type: str = "function"


class SkillsListResponse(BaseModel):
    """Skills 列表响应"""
    skills: list[SkillInfo]


class ExecutionResponse(BaseModel):
    """Skill 执行响应"""
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: int
    skill: str
    executor: Optional[str] = None


@app.get("/", tags=["Root"])
async def root():
    """API 根路径"""
    return {
        "service": "Skills Registry API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/v1/skills", response_model=SkillsListResponse, tags=["Skills"])
async def list_skills():
    """获取所有 Skills

    返回系统中所有已注册的 Skills 列表及其元数据。
    """
    skills = loader.load_all_skills()

    result = []
    for name, info in skills.items():
        metadata = info.get("metadata", {})
        result.append({
            "id": name,
            "title": metadata.get("title"),
            "description": metadata.get("description"),
            "category": metadata.get("category"),
            "enabled": True,  # 暂时默认启用
            "execution_type": metadata.get("execution_type", "function")
        })

    return {"skills": result}


@app.get("/api/v1/skills/{skill_id}", tags=["Skills"])
async def get_skill(skill_id: str):
    """获取单个 Skill 详情

    Args:
        skill_id: Skill 名称

    Returns:
        Skill 的完整元数据
    """
    skills = loader.load_all_skills()
    skill_info = skills.get(skill_id)

    if not skill_info:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

    metadata = skill_info.get("metadata", {})

    return {
        "id": skill_id,
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "category": metadata.get("category"),
        "version": metadata.get("version"),
        "enabled": True,
        "execution_type": metadata.get("execution_type", "function"),
        "path": skill_info.get("path"),
        "has_api": skill_info.get("api_file").exists() if skill_info.get("api_file") else False
    }


@app.post("/api/v1/skills/{skill_id}/execute", response_model=ExecutionResponse, tags=["Execution"])
async def execute_skill(skill_id: str, request: ExecutionRequest):
    """执行 Skill

    Args:
        skill_id: Skill 名称
        request: 执行请求，包含参数和上下文

    Returns:
        执行结果，包含状态、结果或错误信息、执行耗时
    """
    result = await executor.execute(
        skill_id,
        request.params,
        request.context or {}
    )

    # 如果 Skill 不存在，返回 404
    if result["status"] == "error" and "not found" in result.get("error", "").lower():
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """健康检查"""
    skills = loader.load_all_skills()
    return {
        "status": "healthy",
        "total_skills": len(skills),
        "skills_list": list(skills.keys())
    }
