"""认证路由 - Casdoor 集成"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import httpx

from apps.gateway.config import settings
from apps.shared.logger import LogManager

# 创建日志管理器
log_manager = LogManager("gateway", log_dir="logs")
logger = log_manager.get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


CASDOOR_ENDPOINT = settings.casdoor_endpoint.rstrip("/")
CLIENT_ID = settings.casdoor_client_id
CLIENT_SECRET = settings.casdoor_client_secret
REDIRECT_URI = settings.casdoor_redirect_uri

AUTHORIZE_URL = f"{CASDOOR_ENDPOINT}/login/oauth/authorize"
TOKEN_URL = f"{CASDOOR_ENDPOINT}/api/login/oauth/access_token"
USERINFO_URL = f"{CASDOOR_ENDPOINT}/api/userinfo" # OIDC compliant
LOGOUT_URL = f"{CASDOOR_ENDPOINT}/api/logout"
SSO_LOGOUT_URL = f"{CASDOOR_ENDPOINT}/api/sso-logout"


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_expires_in: Optional[int] = None


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    sub: str
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    roles: list = []


@router.get("/login-url")
async def get_login_url(redirect_uri: str = REDIRECT_URI):
    """
    获取登录 URL
    """
    auth_url = (
        f"{AUTHORIZE_URL}"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&scope=openid profile email"
        f"&redirect_uri={redirect_uri}"
        f"&state=rshanygen" 
    )
    return {"login_url": auth_url}


@router.get("/logout-url")
async def get_logout_url(redirect_uri: Optional[str] = None):
    """
    获取登出 URL (Casdoor)
    """
    target_url = redirect_uri or REDIRECT_URI
    
    # 如果是回调地址，尝试去除 /callback 得到首页
    if target_url.endswith("/callback"):
        target_url = target_url[:-9]  # len("/callback") == 9

    from urllib.parse import quote
    encoded_redirect = quote(target_url, safe="")
    
    logout_url = f"{LOGOUT_URL}?post_logout_redirect_uri={encoded_redirect}"
    return {"logout_url": logout_url}


@router.post("/sso-logout")
async def sso_logout(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(SSO_LOGOUT_URL, headers={"Authorization": auth_header})
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"SSO logout failed: {e}")
            raise HTTPException(status_code=400, detail="SSO logout failed")


@router.post("/token", response_model=TokenResponse)
async def exchange_code(code: str, redirect_uri: str = REDIRECT_URI):
    """
    交换授权码获取 Token (授权码流程)
    """
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Casdoor access_token endpoint often uses POST form or query params
            # Let's try POST json first, or form
            response = await client.post(TOKEN_URL, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            # Casdoor response might differ slightly, check documentation
            # Usually: { "access_token": "...", "token_type": "Bearer", ... }
            
            return TokenResponse(
                access_token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
                refresh_expires_in=token_data.get("refresh_expires_in"),
            )

        except httpx.HTTPError as e:
            logger.error(f"Token exchange failed: {e}")
            raise HTTPException(
                status_code=400,
                detail="Failed to exchange authorization code for token"
            )


@router.get("/userinfo", response_model=UserInfoResponse)
async def get_userinfo(request: Request):
    """
    获取当前用户信息
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(USERINFO_URL, headers={"Authorization": auth_header})
            response.raise_for_status()
            data = response.json()
            return UserInfoResponse(
                sub=str(data.get("id") or data.get("sub") or ""),
                username=data.get("name") or data.get("username") or "",
                email=data.get("email"),
                name=data.get("displayName") or data.get("name"),
                roles=data.get("roles") or [],
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            logger.error(f"Userinfo fetch failed: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch userinfo")
        except httpx.HTTPError as e:
            logger.error(f"Userinfo fetch error: {e}")
            raise HTTPException(status_code=503, detail="Authentication service unavailable")


@router.get("/config")
async def get_auth_config():
    """
    获取认证配置 (用于前端)
    """
    return {
        "casdoor_endpoint": CASDOOR_ENDPOINT,
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "organization_name": settings.casdoor_organization_name,
        "application_name": settings.casdoor_application_name,
        "login_url": (
            f"{AUTHORIZE_URL}"
            f"?client_id={CLIENT_ID}"
            f"&response_type=code"
            f"&scope=openid profile email"
            f"&redirect_uri={REDIRECT_URI}"
            f"&state=rshanygen"
        )
    }
