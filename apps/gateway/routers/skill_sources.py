"""Skill Sources 管理 API（代理 Skills Registry）。"""

from __future__ import annotations

from typing import Optional

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel

from apps.gateway.middleware.auth import require_any_role, require_auth
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("gateway")
logger = logger_manager.get_logger()


class CreateSourceRequest(BaseModel):
    repo_url: str
    name: Optional[str] = None
    subdir: str = "skills"
    ref: Optional[str] = None
    id: Optional[str] = None
    enabled: bool = True
    description: Optional[str] = None


class ToggleSourceRequest(BaseModel):
    enabled: bool


class InstallFromSourceRequest(BaseModel):
    slug: str
    overwrite: bool = False


router = APIRouter(
    prefix="/api/v1/skill-sources",
    tags=["skill-sources"],
    dependencies=[Depends(require_auth)],
)

SKILLS_REGISTRY_URL = config.get("services.skills_registry.url", "http://localhost:9303")


def _detail_from_resp(resp: httpx.Response) -> str:
    try:
        if resp.headers.get("content-type", "").startswith("application/json"):
            data = resp.json()
            if isinstance(data, dict) and "detail" in data:
                return str(data.get("detail"))
    except Exception:
        pass
    return resp.text


@router.get("")
async def list_sources():
    logger.info("Listing skill sources from registry")
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            resp = await client.get(f"{SKILLS_REGISTRY_URL}/api/v1/skill-sources")
            if resp.status_code != 200:
                logger.error(f"Failed to list sources: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.post("")
async def create_source(
    request: CreateSourceRequest = Body(...),
    _user=Depends(require_any_role(["admin"])),
):
    logger.info(f"Creating skill source: {request.repo_url}")
    try:
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            resp = await client.post(
                f"{SKILLS_REGISTRY_URL}/api/v1/skill-sources",
                json=request.model_dump(),
            )
            if resp.status_code in (400, 404):
                raise HTTPException(status_code=resp.status_code, detail=_detail_from_resp(resp))
            if resp.status_code != 200:
                logger.error(f"Failed to create source: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.post("/{source_id}/toggle")
async def toggle_source(
    source_id: str,
    request: ToggleSourceRequest = Body(...),
    _user=Depends(require_any_role(["admin"])),
):
    logger.info(f"Toggling skill source {source_id} to {request.enabled}")
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            resp = await client.post(
                f"{SKILLS_REGISTRY_URL}/api/v1/skill-sources/{source_id}/toggle",
                json={"enabled": request.enabled},
            )
            if resp.status_code in (400, 404):
                raise HTTPException(status_code=resp.status_code, detail=_detail_from_resp(resp))
            if resp.status_code != 200:
                logger.error(f"Failed to toggle source: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    _user=Depends(require_any_role(["admin"])),
):
    logger.info(f"Deleting skill source: {source_id}")
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            resp = await client.delete(f"{SKILLS_REGISTRY_URL}/api/v1/skill-sources/{source_id}")
            if resp.status_code in (400, 404):
                raise HTTPException(status_code=resp.status_code, detail=_detail_from_resp(resp))
            if resp.status_code != 200:
                logger.error(f"Failed to delete source: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.get("/{source_id}/skills")
async def list_source_skills(
    source_id: str,
    refresh: bool = Query(False),
):
    logger.info(f"Listing skills in source {source_id} (refresh={refresh})")
    try:
        async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
            resp = await client.get(
                f"{SKILLS_REGISTRY_URL}/api/v1/skill-sources/{source_id}/skills",
                params={"refresh": int(refresh)},
            )
            if resp.status_code in (400, 404):
                raise HTTPException(status_code=resp.status_code, detail=_detail_from_resp(resp))
            if resp.status_code != 200:
                logger.error(f"Failed to list source skills: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.get("/skills")
async def list_all_source_skills(
    refresh: bool = Query(False),
    enabled_only: bool = Query(True, alias="enabled_only"),
):
    logger.info(f"Listing skills across all sources (refresh={refresh}, enabled_only={enabled_only})")
    try:
        async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
            resp = await client.get(
                f"{SKILLS_REGISTRY_URL}/api/v1/skill-sources/skills",
                params={"refresh": int(refresh), "enabled_only": int(enabled_only)},
            )
            if resp.status_code in (400, 404):
                raise HTTPException(status_code=resp.status_code, detail=_detail_from_resp(resp))
            if resp.status_code != 200:
                logger.error(f"Failed to list all source skills: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.post("/{source_id}/install")
async def install_from_source(
    source_id: str,
    request: InstallFromSourceRequest = Body(...),
    _user=Depends(require_any_role(["admin"])),
):
    logger.info(f"Installing skill from source {source_id}: {request.slug}")
    try:
        async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
            resp = await client.post(
                f"{SKILLS_REGISTRY_URL}/api/v1/skill-sources/{source_id}/install",
                json=request.model_dump(),
            )
            if resp.status_code in (400, 404):
                raise HTTPException(status_code=resp.status_code, detail=_detail_from_resp(resp))
            if resp.status_code != 200:
                logger.error(f"Failed to install from source: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")


@router.post("/{source_id}/install-async")
async def install_from_source_async(
    source_id: str,
    request: InstallFromSourceRequest = Body(...),
    _user=Depends(require_any_role(["admin"])),
):
    """异步从 Source 安装 Skill（返回 job_id）"""
    logger.info(f"Installing skill async from source {source_id}: {request.slug}")
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            resp = await client.post(
                f"{SKILLS_REGISTRY_URL}/api/v1/skill-sources/{source_id}/install-async",
                json=request.model_dump(),
            )
            if resp.status_code in (400, 404):
                raise HTTPException(status_code=resp.status_code, detail=_detail_from_resp(resp))
            if resp.status_code != 200:
                logger.error(f"Failed to start install job from source: {resp.status_code} {resp.text}")
                raise HTTPException(status_code=503, detail="Skills Registry unavailable")
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Skills Registry: {e}")
        raise HTTPException(status_code=503, detail="Skills Registry unreachable")
