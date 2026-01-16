"""MCP Transport Layer Tests"""

import pytest
from apps.mcp_manager.transport.factory import MCPTransportFactory
from apps.mcp_manager.transport.stdio import StdioTransport
from apps.mcp_manager.transport.http import HTTPTransport
from apps.mcp_manager.transport.sse import SSETransport


@pytest.mark.unit
def test_factory_creates_stdio_transport():
    """测试：工厂创建 stdio 传输"""
    config = {
        "transport": "stdio",
        "command": "python",
        "args": ["-m", "test.server"]
    }
    transport = MCPTransportFactory.create(config)

    assert isinstance(transport, StdioTransport)
    assert transport.command == "python"
    assert transport.args == ["-m", "test.server"]


@pytest.mark.unit
def test_factory_creates_http_transport():
    """测试：工厂创建 HTTP 传输"""
    config = {
        "transport": "http",
        "url": "http://localhost:8080/mcp"
    }
    transport = MCPTransportFactory.create(config)

    assert isinstance(transport, HTTPTransport)
    assert transport.url == "http://localhost:8080/mcp"


@pytest.mark.unit
def test_factory_creates_sse_transport():
    """测试：工厂创建 SSE 传输"""
    config = {
        "transport": "sse",
        "url": "http://localhost:8080/mcp",
        "timeout": 90000
    }
    transport = MCPTransportFactory.create(config)

    assert isinstance(transport, SSETransport)
    assert transport.url == "http://localhost:8080/mcp"
    assert transport.timeout == 90


@pytest.mark.unit
def test_factory_unsupported_transport():
    """测试：不支持的传输类型应抛出错误"""
    config = {"transport": "unsupported"}

    with pytest.raises(ValueError, match="Unsupported transport type"):
        MCPTransportFactory.create(config)


@pytest.mark.unit
def test_stdio_transport_initialization():
    """测试：stdio 传输初始化"""
    transport = StdioTransport(
        command="node",
        args=["server.js"],
        env={"NODE_ENV": "test"}
    )

    assert transport.command == "node"
    assert transport.args == ["server.js"]
    assert transport.env == {"NODE_ENV": "test"}
    assert transport.process is None


@pytest.mark.unit
def test_http_transport_initialization():
    """测试：HTTP 传输初始化"""
    transport = HTTPTransport(
        url="http://localhost:3000/mcp",
        headers={"Authorization": "Bearer token"},
        timeout=45000
    )

    assert transport.url == "http://localhost:3000/mcp"
    assert transport.headers == {"Authorization": "Bearer token"}
    assert transport.timeout == 45


@pytest.mark.unit
def test_sse_transport_initialization():
    """测试：SSE 传输初始化"""
    transport = SSETransport(
        url="http://localhost:3000/events",
        headers={"X-Custom-Header": "value"},
        timeout=120000
    )

    assert transport.url == "http://localhost:3000/events"
    assert transport.headers == {"X-Custom-Header": "value"}
    assert transport.timeout == 120


@pytest.mark.unit
def test_transport_defaults():
    """测试：传输层默认值"""
    # HTTP with defaults
    http_config = {"transport": "http", "url": "http://localhost:8080"}
    http_transport = MCPTransportFactory.create(http_config)
    assert http_transport.headers == {}
    assert http_transport.timeout == 30

    # SSE with defaults
    sse_config = {"transport": "sse", "url": "http://localhost:8080"}
    sse_transport = MCPTransportFactory.create(sse_config)
    assert sse_transport.headers == {}
    assert sse_transport.timeout == 60

    # stdio with defaults
    stdio_config = {"transport": "stdio", "command": "python"}
    stdio_transport = MCPTransportFactory.create(stdio_config)
    assert stdio_transport.args == []
    assert stdio_transport.env == {}


@pytest.mark.unit
def test_stdio_not_connected_initially():
    """测试：stdio 传输初始未连接状态"""
    transport = StdioTransport(command="python", args=[])
    assert not transport.is_connected()


@pytest.mark.unit
def test_http_not_connected_initially():
    """测试：HTTP 传输初始未连接状态"""
    transport = HTTPTransport(url="http://localhost:8080")
    assert not transport.is_connected()


@pytest.mark.unit
def test_sse_not_connected_initially():
    """测试：SSE 传输初始未连接状态"""
    transport = SSETransport(url="http://localhost:8080")
    assert not transport.is_connected()
