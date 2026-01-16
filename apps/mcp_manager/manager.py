"""MCP 服务统一管理器"""
from typing import Dict, List, Optional, Any
from .transport.factory import MCPTransportFactory
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager


class MCPManager:
    """MCP 服务统一管理器"""

    def __init__(self, config_path: str = "config/mcp.yaml"):
        """
        初始化 MCP 管理器

        Args:
            config_path: MCP 配置文件路径
        """
        self.config_loader = ConfigLoader()
        self.connections: Dict[str, Any] = {}
        self.tools_cache: Dict[str, List[dict]] = {}
        self.log_manager = LogManager("mcp-manager")
        self.logger = self.log_manager.get_logger()
        self.config = self._load_config(config_path)

    def _load_config(self, path: str) -> dict:
        """
        加载 MCP 配置

        Args:
            path: 配置文件路径

        Returns:
            配置字典
        """
        import yaml
        from pathlib import Path

        config_path = Path(path)
        if not config_path.exists():
            self.logger.warning(f"Config file not found: {path}, using empty config")
            return {"servers": {}}

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            self.logger.info(f"Loaded MCP config from {path}")
            return config

    async def discover_servers(self) -> List[str]:
        """
        发现所有可用的 MCP Server

        Returns:
            服务器名称列表
        """
        servers = []
        for name, config in self.config.get("servers", {}).items():
            if config.get("enabled", True):
                servers.append(name)
                self.logger.info(f"Discovered MCP server: {name}")
        return servers

    async def connect_server(self, server_name: str) -> bool:
        """
        连接到指定的 MCP Server

        Args:
            server_name: 服务器名称

        Returns:
            连接是否成功
        """
        if server_name in self.connections:
            client = self.connections[server_name]
            if hasattr(client, 'is_connected') and client.is_connected():
                self.logger.info(f"Already connected to {server_name}")
                return True

        if server_name not in self.config.get("servers", {}):
            self.logger.error(f"Server not found in config: {server_name}")
            return False

        server_config = self.config["servers"][server_name]
        try:
            client = MCPTransportFactory.create(server_config)
            self.logger.info(f"Created transport for {server_name}: {server_config.get('transport')}")

            if await client.connect():
                self.connections[server_name] = client
                self.logger.info(f"Successfully connected to {server_name}")
                return True
            else:
                self.logger.error(f"Failed to connect to {server_name}")
                return False
        except Exception as e:
            self.logger.error(f"Error connecting to {server_name}: {e}")
            return False

    async def list_tools(self, server_name: str) -> List[dict]:
        """
        列出指定 Server 的可用工具

        Args:
            server_name: 服务器名称

        Returns:
            工具列表
        """
        client = self.connections.get(server_name)
        if not client or not client.is_connected():
            self.logger.info(f"Connecting to {server_name} for tool listing")
            await self.connect_server(server_name)
            client = self.connections.get(server_name)

        if not client:
            self.logger.error(f"Failed to get client for {server_name}")
            return []

        try:
            result = await client.send_request("tools/list", {})
            tools = result.get("tools", [])
            self.tools_cache[server_name] = tools
            self.logger.info(f"Listed {len(tools)} tools from {server_name}")
            return tools
        except Exception as e:
            self.logger.error(f"Error listing tools from {server_name}: {e}")
            return []

    async def call_tool(
        self,
        server: str,
        tool: str,
        args: dict
    ) -> dict:
        """
        调用 MCP 工具

        Args:
            server: 服务器名称
            tool: 工具名称
            args: 工具参数

        Returns:
            工具执行结果
        """
        client = self.connections.get(server)
        if not client or not client.is_connected():
            self.logger.info(f"Connecting to {server} for tool call")
            await self.connect_server(server)
            client = self.connections.get(server)

        if not client:
            self.logger.error(f"Failed to get client for {server}")
            return {"error": f"Not connected to {server}"}

        try:
            self.logger.info(f"Calling tool {tool} on {server} with args: {args}")
            result = await client.send_request("tools/call", {
                "name": tool,
                "arguments": args
            })
            return result
        except Exception as e:
            self.logger.error(f"Error calling tool {tool} on {server}: {e}")
            return {"error": str(e)}

    async def disconnect_server(self, server_name: str) -> bool:
        """
        断开指定服务器的连接

        Args:
            server_name: 服务器名称

        Returns:
            是否成功断开
        """
        if server_name not in self.connections:
            self.logger.warning(f"No connection found for {server_name}")
            return True

        try:
            client = self.connections[server_name]
            await client.disconnect()
            del self.connections[server_name]
            self.logger.info(f"Disconnected from {server_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error disconnecting from {server_name}: {e}")
            return False

    async def disconnect_all(self):
        """断开所有连接"""
        for server_name in list(self.connections.keys()):
            await self.disconnect_server(server_name)
        self.logger.info("Disconnected all MCP servers")

    def __del__(self):
        """析构函数，确保资源释放"""
        if hasattr(self, 'log_manager'):
            self.log_manager.close()
