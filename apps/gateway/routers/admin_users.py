from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.gateway.middleware.auth import require_any_role
from apps.gateway.services.keycloak_admin import KeycloakAdminClient


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_any_role(["admin"]))],
)


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    enabled: bool = True
    password: Optional[str] = None
    temporary_password: bool = True


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    enabled: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6)
    temporary: bool = True


class UpdateRolesRequest(BaseModel):
    add: List[str] = []
    remove: List[str] = []


@router.get("/users")
async def list_users(search: Optional[str] = None, first: int = 0, max: int = 50):
    client = KeycloakAdminClient()
    try:
        return await client.list_users(search=search, first=first, max=max)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Keycloak admin error: {str(e)}")


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    client = KeycloakAdminClient()
    try:
        return await client.get_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Keycloak admin error: {str(e)}")


@router.post("/users")
async def create_user(request: CreateUserRequest):
    client = KeycloakAdminClient()
    payload: Dict[str, Any] = {
        "username": request.username,
        "enabled": request.enabled,
    }
    if request.email is not None:
        payload["email"] = request.email
        payload["emailVerified"] = False
    if request.first_name is not None:
        payload["firstName"] = request.first_name
    if request.last_name is not None:
        payload["lastName"] = request.last_name

    try:
        user_id = await client.create_user(payload)
        if request.password:
            await client.reset_password(user_id, request.password, temporary=request.temporary_password)
        return {"id": user_id}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Keycloak admin error: {str(e)}")


@router.patch("/users/{user_id}")
async def update_user(user_id: str, request: UpdateUserRequest):
    client = KeycloakAdminClient()
    payload: Dict[str, Any] = {}
    if request.email is not None:
        payload["email"] = request.email
    if request.first_name is not None:
        payload["firstName"] = request.first_name
    if request.last_name is not None:
        payload["lastName"] = request.last_name
    if request.enabled is not None:
        payload["enabled"] = request.enabled

    try:
        await client.update_user(user_id, payload)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Keycloak admin error: {str(e)}")


@router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: str, request: ResetPasswordRequest):
    client = KeycloakAdminClient()
    try:
        await client.reset_password(user_id, request.password, temporary=request.temporary)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Keycloak admin error: {str(e)}")


@router.get("/roles")
async def list_roles():
    client = KeycloakAdminClient()
    try:
        return await client.list_realm_roles()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Keycloak admin error: {str(e)}")


@router.post("/users/{user_id}/roles")
async def update_user_roles(user_id: str, request: UpdateRolesRequest):
    client = KeycloakAdminClient()
    try:
        if request.add:
            await client.add_realm_roles(user_id, request.add)
        if request.remove:
            await client.remove_realm_roles(user_id, request.remove)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Keycloak admin error: {str(e)}")
