"""JWT 认证中间件 - OIDC"""
from fastapi import Request, Response, status, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional, Sequence
import httpx
from jose import jwt, jwk
from jose.exceptions import JWTError, ExpiredSignatureError
import asyncio
from functools import lru_cache

from apps.gateway.config import settings
from apps.shared.logger import LogManager

# 创建日志管理器
log_manager = LogManager("gateway", log_dir="logs")
logger = log_manager.get_logger()


class JWKsCache:
    """JWKS 缓存 - 定期刷新公钥"""

    def __init__(self):
        self._jwks: dict = {}
        self._lock = asyncio.Lock()
        self._url = settings.jwt_jwks_url

    async def get_jwks(self) -> dict:
        """获取 JWKS (带缓存)"""
        if not self._jwks:
            await self._refresh_jwks()
        return self._jwks

    async def _refresh_jwks(self):
        """刷新 JWKS"""
        async with self._lock:
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(self._url)
                    response.raise_for_status()
                    self._jwks = response.json()
                    logger.info(f"Refreshed JWKS from {self._url}")
                except httpx.HTTPError as e:
                    logger.error(f"Failed to fetch JWKS: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Authentication service unavailable"
                    )

    async def refresh_if_needed(self):
        """定期刷新 JWKS"""
        await self._refresh_jwks()


# 全局 JWKS 缓存实例
_jwks_cache = JWKsCache()


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    JWT 认证中间件

    从 Authorization header 提取 Bearer token，验证并解析用户信息
    将用户信息存入 request.state.user
    """

    # 跳过认证的路径
    EXCLUDE_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/login",
        "/auth/callback",
        "/auth/sso-logout",
    }

    def __init__(self, app):
        super().__init__(app)
        self.issuer = settings.jwt_issuer
        self.audience = settings.jwt_audience
        self.algorithm = settings.jwt_algorithm
        self.userinfo_url = f"{settings.casdoor_endpoint.rstrip('/')}/api/userinfo"

    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求，验证 JWT token"""

        # 跳过特定路径的认证
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        # 跳过 OPTIONS 请求 (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # 提取 Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            # 对于未认证的请求，可以继续但不设置 user
            # 或者直接返回 401 - 根据业务需求决定
            request.state.user = None
            return await call_next(request)

        token = authorization.split(" ")[1]

        try:
            # 获取并验证 token
            payload = await self._verify_token(token)
            await self._validate_token_with_casdoor(token)

            # 提取用户信息
            user_info = {
                "user_id": payload.get("sub"),
                "username": payload.get("preferred_username") or payload.get("email"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "roles": (
                    payload.get("roles")
                    or payload.get("authorities")
                    or payload.get("realm_access", {}).get("roles", [])
                ),
                "exp": payload.get("exp"),
            }
            request.state.user = user_info
            logger.debug(f"Authenticated user: {user_info['username']}")

        except (JWTError, ExpiredSignatureError) as e:
            logger.warning(f"JWT validation failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)

    async def _verify_token(self, token: str) -> dict:
        """验证 JWT token"""
        # 获取 JWKS
        jwks = await _jwks_cache.get_jwks()

        # 解析 token header 获取 kid
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        if not kid:
            raise JWTError("Token missing key ID")

        # 从 JWKS 中找到对应的公钥
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = {
                    "kty": key.get("kty"),
                    "kid": key.get("kid"),
                    "use": key.get("use"),
                    "n": key.get("n"),
                    "e": key.get("e"),
                }
                break

        if not rsa_key:
            raise JWTError(f"Unable to find a signing key that matches: {kid}")

        # 验证 token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=[self.algorithm],
            audience=self.audience,
            issuer=self.issuer,
            options={
                "verify_aud": False,
                "verify_iss": True,
            }
        )

        return payload

    async def _validate_token_with_casdoor(self, token: str) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code >= 400:
                raise JWTError("Token invalidated")


async def get_current_user(request: Request) -> Optional[dict]:
    """获取当前认证用户 (依赖注入函数)"""
    return getattr(request.state, "user", None)


async def require_auth(request: Request) -> dict:
    """要求认证的依赖注入函数"""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def require_any_role(required_roles: Sequence[str]):
    async def _dep(request: Request) -> dict:
        user = await require_auth(request)
        user_roles = set(user.get("roles") or [])
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _dep
