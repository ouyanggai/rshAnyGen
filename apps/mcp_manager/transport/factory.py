"""MCP Transport Factory"""

from typing import Dict
from .abc import MCPTransport
from .stdio import StdioTransport
from .http import HTTPTransport
from .sse import SSETransport


class MCPTransportFactory:
    """MCP 客户端工厂"""

    @staticmethod
    def create(config: dict) -> MCPTransport:
        """根据配置创建对应的传输客户端"""
        transport_type = config.get("transport", "stdio")

        if transport_type == "stdio":
            return StdioTransport(
                command=config["command"],
                args=config.get("args", []),
                env=config.get("env", {})
            )
        elif transport_type == "http":
            return HTTPTransport(
                url=config["url"],
                headers=config.get("headers"),
                timeout=config.get("timeout", 30000)
            )
        elif transport_type == "sse":
            return SSETransport(
                url=config["url"],
                headers=config.get("headers"),
                timeout=config.get("timeout", 60000)
            )
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")
