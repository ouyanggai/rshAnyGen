"""MCP 管理器单元测试"""
import pytest
from apps.mcp_manager.manager import MCPManager
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.unit
def test_manager_initialization():
    """测试 MCP 管理器初始化"""
    manager = MCPManager()

    assert manager.config is not None
    assert "servers" in manager.config
    assert manager.connections == {}
    assert manager.tools_cache == {}
    assert manager.logger is not None
    assert hasattr(manager, 'log_manager')

    manager.log_manager.close()


@pytest.mark.unit
def test_manager_config_loading():
    """测试配置加载"""
    manager = MCPManager("config/mcp.yaml")

    assert isinstance(manager.config, dict)
    assert "servers" in manager.config

    manager.log_manager.close()


@pytest.mark.unit
def test_manager_config_not_found():
    """测试配置文件不存在的情况"""
    manager = MCPManager("non/existent/path.yaml")

    # 应该返回空配置而不是报错
    assert manager.config == {"servers": {}}

    manager.log_manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_discover_servers():
    """测试发现服务器"""
    manager = MCPManager()

    servers = await manager.discover_servers()

    assert isinstance(servers, list)
    # 所有返回的服务器都应该在配置中
    for server in servers:
        assert server in manager.config.get("servers", {})

    manager.log_manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_discover_servers_with_disabled():
    """测试发现服务器时过滤禁用的服务器"""
    # 创建一个模拟配置，其中包含禁用的服务器
    with patch('apps.mcp_manager.manager.MCPManager._load_config') as mock_load:
        mock_load.return_value = {
            "servers": {
                "enabled-server": {"enabled": True, "transport": "stdio", "command": "test"},
                "disabled-server": {"enabled": False, "transport": "stdio", "command": "test"}
            }
        }

        manager = MCPManager()
        servers = await manager.discover_servers()

        assert "enabled-server" in servers
        assert "disabled-server" not in servers

        manager.log_manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_connect_non_existent_server():
    """测试连接不存在的服务器"""
    manager = MCPManager()

    result = await manager.connect_server("non-existent-server")

    assert result is False
    assert "non-existent-server" not in manager.connections

    manager.log_manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_list_tools_non_existent_server():
    """测试列出不存在服务器的工具"""
    manager = MCPManager()

    tools = await manager.list_tools("non-existent-server")

    assert tools == []

    manager.log_manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_call_tool_non_existent_server():
    """测试调用不存在服务器的工具"""
    manager = MCPManager()

    result = await manager.call_tool("non-existent", "search", {"query": "test"})

    assert "error" in result

    manager.log_manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_disconnect_all():
    """测试断开所有连接"""
    manager = MCPManager()

    # 即使没有连接，也不应该报错
    await manager.disconnect_all()

    assert len(manager.connections) == 0

    manager.log_manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manager_disconnect_server():
    """测试断开指定服务器"""
    manager = MCPManager()

    # 断开不存在的连接不应该报错
    result = await manager.disconnect_server("non-existent")

    assert result is True

    manager.log_manager.close()
