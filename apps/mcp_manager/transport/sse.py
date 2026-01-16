"""SSE Transport Implementation"""

import json
import httpx
import urllib.parse
from typing import Optional
from .abc import MCPTransport


class SSETransport(MCPTransport):
    """SSE 传输实现"""

    def __init__(self, url: str, headers: dict = None, timeout: int = 60):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout / 1000
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """建立 SSE 连接"""
        self.client = httpx.AsyncClient(headers=self.headers, timeout=self.timeout)
        return True

    async def disconnect(self) -> bool:
        """关闭连接"""
        if self.client:
            await self.client.aclose()
            return True
        return False

    async def send_request(self, method: str, params: dict) -> dict:
        """通过 SSE 发送请求"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        params_str = urllib.parse.urlencode({"request": json.dumps(request)})

        async with self.client.stream("GET", f"{self.url}?{params_str}") as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("id") == 1:
                        return data
        return {}

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.client is not None
