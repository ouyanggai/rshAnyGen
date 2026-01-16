"""HTTP Transport Implementation"""

import httpx
from typing import Optional
from .abc import MCPTransport


class HTTPTransport(MCPTransport):
    """HTTP 传输实现"""

    def __init__(self, url: str, headers: dict = None, timeout: int = 30):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout / 1000
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """创建 HTTP 客户端"""
        self.client = httpx.AsyncClient(headers=self.headers, timeout=self.timeout)
        # 测试连接
        try:
            response = await self.client.get(f"{self.url}/health")
            return response.status_code == 200
        except:
            return False

    async def disconnect(self) -> bool:
        """关闭 HTTP 客户端"""
        if self.client:
            await self.client.aclose()
            return True
        return False

    async def send_request(self, method: str, params: dict) -> dict:
        """发送 HTTP POST 请求"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        response = await self.client.post(f"{self.url}/rpc", json=request)
        return response.json()

    def is_connected(self) -> bool:
        """检查客户端状态"""
        return self.client is not None
