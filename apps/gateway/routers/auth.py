"""认证路由 - Keycloak OIDC 集成"""
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional
import httpx
from jose import jwt

from apps.gateway.config import settings
from apps.shared.logger import LogManager

# 创建日志管理器
log_manager = LogManager("gateway", log_dir="logs")
logger = log_manager.get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Keycloak URLs
KEYCLOAK_URL = settings.keycloak_url
REALM = settings.keycloak_realm
FRONTEND_CLIENT_ID = settings.keycloak_frontend_client_id
BACKEND_CLIENT_ID = settings.keycloak_backend_client_id
BACKEND_CLIENT_SECRET = settings.keycloak_backend_client_secret


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    refresh_expires_in: Optional[int] = None


class TokenIntrospectResponse(BaseModel):
    """Token 内省响应"""
    active: bool
    username: Optional[str] = None
    exp: Optional[int] = None


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    sub: str
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    roles: list = []


@router.get("/login-url")
async def get_login_url(redirect_uri: str = "http://localhost:9300/"):
    """
    获取 Keycloak 登录 URL

    前端使用此 URL 重定向用户到 Keycloak 登录页面
    """
    auth_url = (
        f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/auth"
        f"?client_id={FRONTEND_CLIENT_ID}"
        f"&response_type=code"
        f"&scope=openid profile email"
        f"&redirect_uri={redirect_uri}"
    )
    return {"login_url": auth_url}


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    直接登录 (Resource Owner Password Credentials Flow)

    用于测试或后台管理，前端应使用授权码流程
    """
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"

    data = {
        "client_id": BACKEND_CLIENT_ID,
        "client_secret": BACKEND_CLIENT_SECRET,
        "username": request.username,
        "password": request.password,
        "grant_type": "password",
        "scope": "openid profile email",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

            return TokenResponse(
                access_token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                refresh_expires_in=token_data.get("refresh_expires_in"),
            )

        except httpx.HTTPError as e:
            logger.error(f"Login failed: {e}")
            raise HTTPException(
                status_code=401,
                detail="Login failed. Please check your credentials."
            )


@router.post("/token", response_model=TokenResponse)
async def exchange_code(code: str, redirect_uri: str = "http://localhost:9300/"):
    """
    交换授权码获取 Token (授权码流程)

    前端获取授权码后，调用此接口交换 token
    """
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"

    data = {
        "client_id": FRONTEND_CLIENT_ID,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

            return TokenResponse(
                access_token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                refresh_expires_in=token_data.get("refresh_expires_in"),
            )

        except httpx.HTTPError as e:
            logger.error(f"Token exchange failed: {e}")
            raise HTTPException(
                status_code=400,
                detail="Failed to exchange authorization code for token"
            )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """使用 refresh_token 获取新的 access_token"""
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"

    data = {
        "client_id": BACKEND_CLIENT_ID,
        "client_secret": BACKEND_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

            return TokenResponse(
                access_token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                refresh_expires_in=token_data.get("refresh_expires_in"),
            )

        except httpx.HTTPError as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(
                status_code=401,
                detail="Failed to refresh token"
            )


@router.post("/logout")
async def logout(refresh_token: Optional[str] = None):
    """
    登出

    如果提供 refresh_token，会同时撤销它
    """
    logout_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/logout"

    data = {
        "client_id": FRONTEND_CLIENT_ID,
    }

    if refresh_token:
        data["refresh_token"] = refresh_token

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(logout_url, data=data)
            response.raise_for_status()
            return {"message": "Logged out successfully"}

        except httpx.HTTPError as e:
            logger.error(f"Logout failed: {e}")
            raise HTTPException(
                status_code=400,
                detail="Failed to logout"
            )


@router.get("/userinfo", response_model=UserInfoResponse)
async def get_userinfo(request: Request):
    """
    获取当前用户信息

    从 JWT token 中提取用户信息
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    return UserInfoResponse(
        sub=user.get("user_id", ""),
        username=user.get("username", ""),
        email=user.get("email"),
        name=user.get("name"),
        roles=user.get("roles", []),
    )


@router.get("/config")
async def get_auth_config():
    """
    获取认证配置 (用于前端)

    返回前端需要的 Keycloak 配置
    """
    return {
        "keycloak_url": KEYCLOAK_URL,
        "realm": REALM,
        "client_id": FRONTEND_CLIENT_ID,
        "issuer": settings.jwt_issuer,
    }


@router.post("/introspect")
async def introspect_token(token: str):
    """
    Token 内省 (验证 token 并获取其信息)

    使用 backend-api client 进行内省
    """
    introspect_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token/introspect"

    data = {
        "client_id": BACKEND_CLIENT_ID,
        "client_secret": BACKEND_CLIENT_SECRET,
        "token": token,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(introspect_url, data=data)
            response.raise_for_status()
            introspect_data = response.json()

            return {
                "active": introspect_data.get("active", False),
                "username": introspect_data.get("username"),
                "exp": introspect_data.get("exp"),
            }

        except httpx.HTTPError as e:
            logger.error(f"Token introspection failed: {e}")
            raise HTTPException(
                status_code=400,
                detail="Token introspection failed"
            )
