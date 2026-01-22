import time
from typing import Any, Dict, List, Optional

import httpx

from apps.gateway.config import settings


class KeycloakAdminClient:
    def __init__(self):
        self._token: Optional[str] = None
        self._token_exp: int = 0
        self._fallback_token: Optional[str] = None
        self._fallback_token_exp: int = 0
        self._base = f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}"
        self._token_url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"
        self._master_token_url = f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token"

    async def close(self):
        return

    async def _get_admin_token(self) -> str:
        now = int(time.time())
        if self._token and now < (self._token_exp - 30):
            return self._token

        data = {
            "grant_type": "client_credentials",
            "client_id": settings.keycloak_backend_client_id,
            "client_secret": settings.keycloak_backend_client_secret,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self._token_url, data=data)
            resp.raise_for_status()
            token_data = resp.json()

        access_token = token_data.get("access_token")
        expires_in = int(token_data.get("expires_in") or 60)
        if not access_token:
            raise RuntimeError("Keycloak admin token missing access_token")

        self._token = access_token
        self._token_exp = now + expires_in
        return access_token

    async def _get_master_admin_token(self) -> Optional[str]:
        if not settings.keycloak_admin_username or not settings.keycloak_admin_password:
            return None

        now = int(time.time())
        if self._fallback_token and now < (self._fallback_token_exp - 30):
            return self._fallback_token

        data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": settings.keycloak_admin_username,
            "password": settings.keycloak_admin_password,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self._master_token_url, data=data)
            resp.raise_for_status()
            token_data = resp.json()

        access_token = token_data.get("access_token")
        expires_in = int(token_data.get("expires_in") or 60)
        if not access_token:
            return None

        self._fallback_token = access_token
        self._fallback_token_exp = now + expires_in
        return access_token

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        token = await self._get_admin_token()
        headers = kwargs.pop("headers", {}) or {}
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"

        url = f"{self._base}{path}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.request(method, url, headers=headers, **kwargs)
            if resp.status_code == 403:
                fallback = await self._get_master_admin_token()
                if fallback:
                    headers["Authorization"] = f"Bearer {fallback}"
                    resp = await client.request(method, url, headers=headers, **kwargs)
            resp.raise_for_status()
            return resp

    async def list_users(self, search: Optional[str] = None, first: int = 0, max: int = 50) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"first": first, "max": max}
        if search:
            params["search"] = search
        resp = await self._request("GET", "/users", params=params)
        return resp.json()

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        resp = await self._request("GET", f"/users/{user_id}")
        return resp.json()

    async def create_user(self, payload: Dict[str, Any]) -> str:
        resp = await self._request("POST", "/users", json=payload)
        location = resp.headers.get("Location") or resp.headers.get("location") or ""
        return location.rstrip("/").split("/")[-1] if location else ""

    async def update_user(self, user_id: str, payload: Dict[str, Any]) -> None:
        await self._request("PUT", f"/users/{user_id}", json=payload)

    async def reset_password(self, user_id: str, password: str, temporary: bool = True) -> None:
        payload = {"type": "password", "value": password, "temporary": temporary}
        await self._request("PUT", f"/users/{user_id}/reset-password", json=payload)

    async def set_enabled(self, user_id: str, enabled: bool) -> None:
        await self.update_user(user_id, {"enabled": enabled})

    async def list_realm_roles(self) -> List[Dict[str, Any]]:
        resp = await self._request("GET", "/roles")
        return resp.json()

    async def get_realm_role(self, role_name: str) -> Dict[str, Any]:
        resp = await self._request("GET", f"/roles/{role_name}")
        return resp.json()

    async def add_realm_roles(self, user_id: str, role_names: List[str]) -> None:
        roles = []
        for name in role_names:
            roles.append(await self.get_realm_role(name))
        await self._request("POST", f"/users/{user_id}/role-mappings/realm", json=roles)

    async def remove_realm_roles(self, user_id: str, role_names: List[str]) -> None:
        roles = []
        for name in role_names:
            roles.append(await self.get_realm_role(name))
        await self._request("DELETE", f"/users/{user_id}/role-mappings/realm", json=roles)
