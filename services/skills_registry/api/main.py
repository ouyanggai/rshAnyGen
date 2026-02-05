"""Skills Registry API 入口"""
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..loader import SkillLoader
from ..executor import SkillExecutor
from ..git_utils import ensure_execution_type, git_clone_with_options, parse_skill_frontmatter
from ..remote import list_skills_in_source
from ..sources import DEFAULT_SOURCES, SkillSourcesService, SkillSourcesStore, normalize_repo_url
from apps.shared.config_loader import ConfigLoader
from apps.shared.redis_client import RedisOperations


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
redis = RedisOperations()
config = ConfigLoader()

# 统一的启用/禁用存储：禁用集合（默认全部启用）
DISABLED_SKILLS_KEY = "skills_registry:disabled"
SOURCE_SKILLS_CACHE_KEY = "skills_registry:source_skills"
SOURCE_SKILLS_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6h
INSTALL_JOBS_KEY_PREFIX = "skills_registry:install_jobs"
INSTALL_JOB_TTL_SECONDS = 24 * 60 * 60  # 24h
INSTALL_JOB_LOGS_MAX = 500

# 用户技能目录（可卸载/可写）
_HERE = Path(__file__).resolve()
# services/skills_registry/api/main.py -> api -> skills_registry -> services -> repo-root
REPO_ROOT = _HERE.parents[3]
USER_SKILLS_DIR = REPO_ROOT / "storage" / "skills"
DELETED_SKILLS_DIR = REPO_ROOT / "storage" / ".deleted"
SOURCES_CONFIG_PATH = REPO_ROOT / "storage" / "skill_sources.yaml"

sources_service = SkillSourcesService(
    store=SkillSourcesStore(SOURCES_CONFIG_PATH),
    defaults=DEFAULT_SOURCES,
)


async def _is_enabled(skill_id: str) -> bool:
    await redis.init()
    disabled = await redis.smembers(DISABLED_SKILLS_KEY)
    return str(skill_id) not in disabled


def _source_cache_key(source_id: str, repo_url: str, ref: Optional[str], subdir: str) -> str:
    raw = f"{source_id}|{repo_url}|{ref or ''}|{subdir}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{SOURCE_SKILLS_CACHE_KEY}:{source_id}:{digest}"


def _git_timeout_seconds() -> int:
    try:
        return int(config.get("skills_registry.git.clone_timeout_seconds", 180))
    except Exception:
        return 180


def _git_env() -> dict[str, str]:
    env = dict(os.environ)

    def _get_env_proxy(*keys: str) -> str:
        for key in keys:
            val = os.environ.get(key)
            if val is None:
                continue
            val = str(val).strip()
            if val:
                return val
        return ""

    http_proxy = str(config.get("network.proxy.http", "") or "").strip()
    https_proxy = str(config.get("network.proxy.https", "") or "").strip()
    all_proxy = str(config.get("network.proxy.all", "") or "").strip()
    no_proxy = str(config.get("network.proxy.no_proxy", "") or "").strip()

    if not http_proxy:
        http_proxy = _get_env_proxy("HTTP_PROXY", "http_proxy")
    if not https_proxy:
        https_proxy = _get_env_proxy("HTTPS_PROXY", "https_proxy")
    if not all_proxy:
        all_proxy = _get_env_proxy("ALL_PROXY", "all_proxy")
    if not no_proxy:
        no_proxy = _get_env_proxy("NO_PROXY", "no_proxy")

    def _set_proxy(key: str, val: str):
        if not val:
            return
        env[key] = val
        env[key.lower()] = val

    _set_proxy("HTTP_PROXY", http_proxy)
    _set_proxy("HTTPS_PROXY", https_proxy)
    _set_proxy("ALL_PROXY", all_proxy)
    _set_proxy("NO_PROXY", no_proxy)

    # Avoid hanging on credential prompt
    env.setdefault("GIT_TERMINAL_PROMPT", "0")

    debug = bool(config.get("skills_registry.git.debug", False))
    if debug:
        env.setdefault("GIT_TRACE", "1")
        env.setdefault("GIT_CURL_VERBOSE", "1")

    return env


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
    version: Optional[str] = None
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


class ToggleSkillRequest(BaseModel):
    enabled: bool


class ToggleSourceRequest(BaseModel):
    enabled: bool


class SkillSourceInfo(BaseModel):
    id: str
    name: str
    repo_url: str
    subdir: str = "skills"
    ref: Optional[str] = None
    enabled: bool = True
    builtin: bool = False
    description: Optional[str] = None


class SkillSourcesListResponse(BaseModel):
    sources: list[SkillSourceInfo]


class CreateSkillSourceRequest(BaseModel):
    repo_url: str
    name: Optional[str] = None
    subdir: str = "skills"
    ref: Optional[str] = None
    id: Optional[str] = None
    enabled: bool = True
    description: Optional[str] = None


class RemoteSkillInfo(BaseModel):
    slug: str
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    execution_type: str = "prompt"
    installed: bool = False
    source_id: str


class RemoteSkillsListResponse(BaseModel):
    source: SkillSourceInfo
    skills: list[RemoteSkillInfo]
    cached: bool = False


class InstallFromSourceRequest(BaseModel):
    slug: str
    overwrite: bool = False


class InstallSkillRequest(BaseModel):
    """从 Git 仓库安装 Skill（复制 SKILL.md + 相关文件到 storage/skills/）"""

    repo_url: str
    skill: str
    subdir: str = "skills"
    ref: Optional[str] = None
    overwrite: bool = False


class DeleteSkillResponse(BaseModel):
    status: str
    deleted_skill_id: str
    moved_to: str


class InstallJobInfo(BaseModel):
    id: str
    type: str
    status: str
    created_at: str
    updated_at: str
    request: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: list[str] = []


def _infer_execution_type(skill_info: dict) -> str:
    metadata = skill_info.get("metadata", {}) or {}
    execution_type = metadata.get("execution_type")
    if execution_type:
        return str(execution_type)
    api_file = skill_info.get("api_file")
    if api_file and getattr(api_file, "exists", None) and api_file.exists():
        return "function"
    return "prompt"


def _job_meta_key(job_id: str) -> str:
    return f"{INSTALL_JOBS_KEY_PREFIX}:{job_id}"


def _job_logs_key(job_id: str) -> str:
    return f"{INSTALL_JOBS_KEY_PREFIX}:{job_id}:logs"


def _job_set(job: dict) -> None:
    key = _job_meta_key(str(job.get("id") or ""))
    redis.client.setex(key, INSTALL_JOB_TTL_SECONDS, json.dumps(job, ensure_ascii=False))


def _job_get(job_id: str) -> dict:
    raw = redis.client.get(_job_meta_key(job_id))
    if not raw:
        raise KeyError("Install job not found")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise KeyError("Install job not found")
    return data


def _job_append_log(job_id: str, line: str) -> None:
    if line is None:
        return
    line = str(line).rstrip("\n")
    if not line:
        return
    key = _job_logs_key(job_id)
    redis.client.rpush(key, line)
    redis.client.ltrim(key, -INSTALL_JOB_LOGS_MAX, -1)


def _job_get_logs(job_id: str, tail: int) -> list[str]:
    tail = int(tail or 0)
    if tail <= 0:
        tail = 200
    tail = min(tail, INSTALL_JOB_LOGS_MAX)
    return list(redis.client.lrange(_job_logs_key(job_id), -tail, -1))


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
    await redis.init()
    disabled = await redis.smembers(DISABLED_SKILLS_KEY)

    result = []
    for name, info in skills.items():
        metadata = info.get("metadata", {})
        result.append({
            "id": name,
            "title": metadata.get("title"),
            "description": metadata.get("description"),
            "category": metadata.get("category"),
            "version": metadata.get("version"),
            "enabled": str(name) not in disabled,
            "execution_type": _infer_execution_type(info)
        })

    return {"skills": result}


@app.get("/api/v1/skill-sources", response_model=SkillSourcesListResponse, tags=["Sources"])
async def list_skill_sources():
    """获取已配置的 Skill Sources（包含内置默认源 + 用户自定义源）"""
    sources = [s.to_dict() for s in sources_service.list_sources()]
    return {"sources": sources}


@app.post("/api/v1/skill-sources", response_model=SkillSourceInfo, tags=["Sources"])
async def create_skill_source(request: CreateSkillSourceRequest):
    """新增一个自定义 Source（git 仓库）"""
    try:
        src = sources_service.add_user_source(
            repo_url=request.repo_url,
            name=request.name,
            subdir=request.subdir,
            ref=request.ref,
            source_id=request.id,
            enabled=request.enabled,
            description=request.description,
        )
        return src.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skill-sources/{source_id}/toggle", response_model=SkillSourceInfo, tags=["Sources"])
async def toggle_skill_source(source_id: str, request: ToggleSourceRequest):
    """启用/禁用某个 Source（对内置源为覆盖配置，对自定义源为更新 enabled）"""
    try:
        src = sources_service.set_enabled(source_id, request.enabled)
        return src.to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/skill-sources/{source_id}", tags=["Sources"])
async def delete_skill_source(source_id: str):
    """删除某个 Source（内置源将被标记为禁用）"""
    try:
        sources_service.delete_source(source_id)
        return {"status": "success", "source_id": source_id}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _get_source_skills_cached(source, refresh: bool) -> tuple[list[dict], bool]:
    await redis.init()
    cache_key = _source_cache_key(source.id, source.repo_url, source.ref, source.subdir)
    if not refresh:
        cached = redis.client.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                if isinstance(data, dict) and isinstance(data.get("skills"), list):
                    return data["skills"], True
                if isinstance(data, list):
                    return data, True
            except Exception:
                pass

    items = await asyncio.to_thread(
        lambda: list_skills_in_source(
            source,
            env=_git_env(),
            timeout_seconds=_git_timeout_seconds(),
        )
    )
    payload = {
        "skills": items,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    redis.client.setex(cache_key, SOURCE_SKILLS_CACHE_TTL_SECONDS, json.dumps(payload, ensure_ascii=False))
    return items, False


@app.get("/api/v1/skill-sources/{source_id}/skills", response_model=RemoteSkillsListResponse, tags=["Sources"])
async def list_source_skills(source_id: str, refresh: bool = False):
    """列出某个 Source 下所有可安装的 skills（不安装，仅索引）。"""
    try:
        source = sources_service.get_source(source_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not source.enabled:
        raise HTTPException(status_code=400, detail="Source 已禁用")

    try:
        items, cached = await _get_source_skills_cached(source, refresh=refresh)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    installed_ids = set(loader.load_all_skills().keys())
    skills = []
    for it in items:
        if not isinstance(it, dict):
            continue
        skills.append(
            {
                "slug": str(it.get("slug") or ""),
                "id": str(it.get("id") or ""),
                "title": it.get("title"),
                "description": it.get("description"),
                "category": it.get("category"),
                "version": it.get("version"),
                "execution_type": str(it.get("execution_type") or "prompt"),
                "installed": str(it.get("id") or "") in installed_ids,
                "source_id": source.id,
            }
        )

    return {"source": source.to_dict(), "skills": skills, "cached": cached}


@app.get("/api/v1/skill-sources/skills", tags=["Sources"])
async def list_all_source_skills(refresh: bool = False, enabled_only: bool = True):
    """聚合所有 Sources 的 skills 列表（可能较慢；默认使用缓存）。"""
    sources = sources_service.list_sources()
    if enabled_only:
        sources = [s for s in sources if s.enabled]

    installed_ids = set(loader.load_all_skills().keys())

    async def _one(s):
        items, cached = await _get_source_skills_cached(s, refresh=refresh)
        return s, items, cached

    results = await asyncio.gather(*[_one(s) for s in sources], return_exceptions=True)

    skills: list[dict] = []
    errors: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            errors.append({"error": str(r)})
            continue
        s, items, _cached = r
        for it in items:
            if not isinstance(it, dict):
                continue
            sid = str(it.get("id") or "")
            skills.append(
                {
                    "slug": str(it.get("slug") or ""),
                    "id": sid,
                    "title": it.get("title"),
                    "description": it.get("description"),
                    "category": it.get("category"),
                    "version": it.get("version"),
                    "execution_type": str(it.get("execution_type") or "prompt"),
                    "installed": sid in installed_ids,
                    "source_id": s.id,
                    "source_name": s.name,
                }
            )

    return {"skills": skills, "errors": errors}


@app.post("/api/v1/skill-sources/{source_id}/install", tags=["Sources"])
async def install_skill_from_source(source_id: str, request: InstallFromSourceRequest):
    """从某个 Source 一键安装指定 skill（slug 为源内相对路径）。"""
    try:
        source = sources_service.get_source(source_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not source.enabled:
        raise HTTPException(status_code=400, detail="Source 已禁用")

    payload = InstallSkillRequest(
        repo_url=source.repo_url,
        skill=request.slug,
        subdir=source.subdir,
        ref=source.ref,
        overwrite=bool(request.overwrite),
    )
    return await install_skill(payload)


@app.post("/api/v1/skill-sources/{source_id}/install-async", response_model=InstallJobInfo, tags=["Sources"])
async def install_skill_from_source_async(source_id: str, request: InstallFromSourceRequest):
    """从某个 Source 异步安装指定 skill（返回 job_id，用于前端轮询）。"""
    try:
        source = sources_service.get_source(source_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not source.enabled:
        raise HTTPException(status_code=400, detail="Source 已禁用")

    payload = InstallSkillRequest(
        repo_url=source.repo_url,
        skill=request.slug,
        subdir=source.subdir,
        ref=source.ref,
        overwrite=bool(request.overwrite),
    )

    job = await _start_install_job(payload, job_type="install_from_source", context={"source_id": source_id, "slug": request.slug})
    return {**job, "logs": []}


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
        "enabled": await _is_enabled(skill_id),
        "execution_type": _infer_execution_type(skill_info),
        "path": skill_info.get("path"),
        "has_api": skill_info.get("api_file").exists() if skill_info.get("api_file") else False
    }


@app.post("/api/v1/skills/{skill_id}/toggle", tags=["Skills"])
async def toggle_skill(skill_id: str, request: ToggleSkillRequest):
    """启用/禁用 Skill（持久化到 Redis）"""
    skills = loader.load_all_skills()
    if skill_id not in skills:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

    await redis.init()
    if request.enabled:
        await redis.srem(DISABLED_SKILLS_KEY, skill_id)
    else:
        await redis.sadd(DISABLED_SKILLS_KEY, skill_id)

    # 返回更新后的 skill 信息
    return await get_skill(skill_id)


def _install_skill_sync(request: InstallSkillRequest, *, on_log=None) -> str:
    USER_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    DELETED_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    repo_url = normalize_repo_url(request.repo_url)
    skill_slug = (request.skill or "").strip().strip("/")
    if not skill_slug:
        raise ValueError("skill 不能为空")
    subdir = (request.subdir or "skills").strip().strip("/")
    if not subdir:
        subdir = "skills"

    def _log(line: str):
        if on_log:
            on_log(line)

    _log(f"开始安装: repo={repo_url} subdir={subdir} skill={skill_slug} ref={request.ref or ''}")

    with tempfile.TemporaryDirectory(prefix="skills_install_") as tmp:
        tmp_repo = Path(tmp) / "repo"
        _log("git clone...")
        git_clone_with_options(
            repo_url,
            tmp_repo,
            request.ref,
            env=_git_env(),
            timeout_seconds=_git_timeout_seconds(),
            on_output=on_log,
        )

        _log("git clone 完成")

        _log("校验技能目录")
        src_dir = (tmp_repo / subdir / skill_slug).resolve()
        if not src_dir.exists() or not src_dir.is_dir():
            raise ValueError(f"未找到技能目录: {subdir}/{skill_slug}")

        _log("解析 SKILL.md")
        skill_md = src_dir / "SKILL.md"
        if not skill_md.exists():
            raise ValueError("技能目录缺少 SKILL.md")

        metadata = parse_skill_frontmatter(skill_md)
        skill_id = (metadata.get("name") or "").strip()
        if not skill_id:
            raise ValueError("SKILL.md frontmatter 缺少 name")

        _log("准备写入技能目录")
        dest_dir = (USER_SKILLS_DIR / skill_id).resolve()
        if dest_dir.exists() and not request.overwrite:
            raise ValueError(f"技能已存在: {skill_id}")

        if dest_dir.exists() and request.overwrite:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_dir = (DELETED_SKILLS_DIR / f"{skill_id}__{ts}").resolve()
            _log(f"覆盖安装：备份旧版本到 {backup_dir}")
            shutil.move(str(dest_dir), str(backup_dir))

        _log(f"复制文件到 {dest_dir}")
        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=request.overwrite)
        ensure_execution_type(dest_dir)

        origin = {
            "repo_url": request.repo_url,
            "normalized_repo_url": repo_url,
            "ref": request.ref,
            "subdir": subdir,
            "skill": skill_slug,
            "installed_at": datetime.now(timezone.utc).isoformat(),
        }
        (dest_dir / "origin.json").write_text(
            json.dumps(origin, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        _log(f"安装完成: {skill_id}")
        return skill_id


async def _run_install_job(job_id: str, payload: InstallSkillRequest) -> None:
    await redis.init()

    def _log(line: str):
        _job_append_log(job_id, line)

    job = _job_get(job_id)
    job["status"] = "running"
    job["updated_at"] = datetime.now(timezone.utc).isoformat()
    _job_set(job)

    try:
        skill_id = await asyncio.to_thread(lambda: _install_skill_sync(payload, on_log=_log))
        await redis.srem(DISABLED_SKILLS_KEY, skill_id)
        result = await get_skill(skill_id)

        job = _job_get(job_id)
        job["status"] = "success"
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        job["result"] = {"skill_id": skill_id, "skill": result}
        job["error"] = None
        _job_set(job)
        _log("Job success.")
    except Exception as e:
        _log(f"Job error: {e}")
        job = _job_get(job_id)
        job["status"] = "error"
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        job["error"] = str(e)
        _job_set(job)


async def _start_install_job(payload: InstallSkillRequest, *, job_type: str, context: dict | None = None) -> dict:
    await redis.init()
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    job = {
        "id": job_id,
        "type": job_type,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "request": payload.model_dump(),
        "context": context or {},
        "result": None,
        "error": None,
    }
    _job_set(job)
    redis.client.delete(_job_logs_key(job_id))
    _job_append_log(job_id, "Job created.")

    asyncio.create_task(_run_install_job(job_id, payload))
    return job


@app.post("/api/v1/skills/install-async", response_model=InstallJobInfo, tags=["Skills"])
async def install_skill_async(request: InstallSkillRequest):
    """异步安装 Skill：返回 job_id，前端可轮询获取进度日志。"""
    try:
        job = await _start_install_job(request, job_type="install_skill", context={})
        return {**job, "logs": []}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/skills/install-jobs/{job_id}", response_model=InstallJobInfo, tags=["Skills"])
async def get_install_job(job_id: str, tail: int = 200):
    """获取安装 Job 状态与日志（tail 默认 200 行）。"""
    await redis.init()
    try:
        job = _job_get(job_id)
        logs = _job_get_logs(job_id, tail=tail)
        return {**job, "logs": logs}
    except KeyError:
        raise HTTPException(status_code=404, detail="Install job not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/skills/install", tags=["Skills"])
async def install_skill(request: InstallSkillRequest):
    """从 Git 仓库安装 Skill 到 storage/skills（不修改内置 skills）"""
    USER_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    DELETED_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        skill_id = await asyncio.to_thread(lambda: _install_skill_sync(request, on_log=None))
        await redis.init()
        await redis.srem(DISABLED_SKILLS_KEY, skill_id)
        return await get_skill(skill_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/skills/{skill_id}", response_model=DeleteSkillResponse, tags=["Skills"])
async def delete_skill(skill_id: str):
    """卸载 Skill（仅允许卸载 storage/skills 下的用户技能）"""
    skills = loader.load_all_skills()
    info = skills.get(skill_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

    path = Path(info.get("path") or "").resolve()
    USER_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    DELETED_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    if not path.is_relative_to(USER_SKILLS_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Built-in skills cannot be deleted")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    moved_to = (DELETED_SKILLS_DIR / f"{skill_id}__{ts}").resolve()

    try:
        await asyncio.to_thread(lambda: shutil.move(str(path), str(moved_to)))
        await redis.init()
        await redis.srem(DISABLED_SKILLS_KEY, skill_id)
        return {
            "status": "success",
            "deleted_skill_id": skill_id,
            "moved_to": str(moved_to),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
