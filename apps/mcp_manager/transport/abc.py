"""MCP Transport Abstract Base Class"""

from abc import ABC, abstractmethod
from typing import Optional, Any


class MCPTransport(ABC):
    """MCP 传输层抽象基类"""

    @abstractmethod
    async def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """断开连接"""
        pass

    @abstractmethod
    async def send_request(self, method: str, params: dict) -> dict:
        """发送 JSON-RPC 请求"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass
