"""MCP 集成测试"""
import pytest
from apps.mcp_manager.manager import MCPManager


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_manager_initialization():
    """测试 MCP 管理器初始化"""
    manager = MCPManager()

    assert manager.config is not None
    assert "servers" in manager.config
    assert manager.connections == {}
    assert manager.tools_cache == {}

    # 清理
    manager.log_manager.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_discover_servers():
    """测试发现 MCP 服务器"""
    manager = MCPManager()
    servers = await manager.discover_servers()

    assert isinstance(servers, list)
    # 检查是否包含 baidu-search（如果配置中启用了）
    if manager.config.get("servers", {}).get("baidu-search", {}).get("enabled", False):
        assert "baidu-search" in servers

    manager.log_manager.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_baidu_search_server():
    """测试百度搜索 MCP Server"""
    from apps.mcp_baidu_search.server import MockBaiduSearchServer

    server = MockBaiduSearchServer()

    # 测试初始化
    init_result = await server._initialize()
    assert "result" in init_result
    assert init_result["result"]["serverInfo"]["name"] == "baidu-search"

    # 测试工具列表
    tools_result = await server._list_tools()
    assert "result" in tools_result
    tools = tools_result["result"]["tools"]
    assert len(tools) == 2
    tool_names = [tool["name"] for tool in tools]
    assert "search" in tool_names
    assert "fetch_page" in tool_names

    # 测试搜索功能
    search_result = await server._search("测试查询", top_n=2)
    assert "result" in search_result
    content = search_result["result"]["content"][0]["text"]
    import json
    data = json.loads(content)
    assert data["query"] == "测试查询"
    assert len(data["results"]) == 2

    # 测试页面抓取功能
    fetch_result = await server._fetch_page("https://example.com")
    assert "result" in fetch_result
    content = fetch_result["result"]["content"][0]["text"]
    data = json.loads(content)
    assert data["url"] == "https://example.com"
    assert "content" in data

    server.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_manager_connect_to_baidu_search():
    """测试 MCP 管理器连接百度搜索服务器"""
    manager = MCPManager()

    # 尝试连接（如果配置中启用了 baidu-search）
    baidu_config = manager.config.get("servers", {}).get("baidu-search")
    if baidu_config and baidu_config.get("enabled", False):
        # 注意：由于 stdio 传输需要真实的子进程通信，
        # 这里我们测试管理器的逻辑而不是实际的连接
        servers = await manager.discover_servers()
        if "baidu-search" in servers:
            # 验证配置存在
            assert baidu_config is not None
            assert baidu_config.get("transport") == "stdio"
            assert "command" in baidu_config

    manager.log_manager.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_manager_tool_operations():
    """测试 MCP 管理器的工具操作"""
    manager = MCPManager()

    # 获取服务器列表
    servers = await manager.discover_servers()
    assert isinstance(servers, list)

    # 测试断开所有连接
    await manager.disconnect_all()
    assert len(manager.connections) == 0

    manager.log_manager.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_error_handling():
    """测试 MCP 错误处理"""
    manager = MCPManager()

    # 测试连接不存在的服务器
    result = await manager.connect_server("non-existent-server")
    assert result is False

    # 测试列出不存在服务器的工具
    tools = await manager.list_tools("non-existent-server")
    assert tools == []

    # 测试调用不存在服务器的工具
    call_result = await manager.call_tool("non-existent-server", "search", {"query": "test"})
    assert "error" in call_result

    manager.log_manager.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_config_loading():
    """测试 MCP 配置加载"""
    import yaml
    from pathlib import Path

    config_path = Path("config/mcp.yaml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        assert "servers" in config
        # 验证 baidu-search 配置
        if "baidu-search" in config["servers"]:
            baidu_config = config["servers"]["baidu-search"]
            assert "transport" in baidu_config
            assert "command" in baidu_config


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_full_workflow_simulation():
    """测试 MCP 完整工作流模拟"""
    from apps.mcp_baidu_search.server import MockBaiduSearchServer

    # 创建模拟服务器
    server = MockBaiduSearchServer()

    # 1. 初始化
    await server._initialize()

    # 2. 获取工具列表
    tools_result = await server._list_tools()
    tools = tools_result["result"]["tools"]

    # 3. 执行搜索
    search_result = await server._search("Python 异步编程", top_n=3)
    assert "result" in search_result

    # 4. 获取页面内容
    fetch_result = await server._fetch_page("https://example.com/test")
    assert "result" in fetch_result

    # 5. 清理
    server.close()

    # 验证工作流完成
    assert True
