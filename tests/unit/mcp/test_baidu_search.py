"""百度搜索 MCP Server 单元测试"""
import pytest
import json
from apps.mcp_baidu_search.server import MockBaiduSearchServer


@pytest.mark.unit
def test_baidu_search_server_initialization():
    """测试百度搜索服务器初始化"""
    server = MockBaiduSearchServer()

    assert server.logger is not None
    assert len(server.tools) == 2

    tool_names = [tool["name"] for tool in server.tools]
    assert "search" in tool_names
    assert "fetch_page" in tool_names

    server.close()


@pytest.mark.unit
def test_baidu_search_tool_definitions():
    """测试工具定义"""
    server = MockBaiduSearchServer()

    # 检查 search 工具定义
    search_tool = next((t for t in server.tools if t["name"] == "search"), None)
    assert search_tool is not None
    assert search_tool["description"] == "在百度搜索引擎中搜索关键词"
    assert "query" in search_tool["inputSchema"]["properties"]
    assert "top_n" in search_tool["inputSchema"]["properties"]
    assert "query" in search_tool["inputSchema"]["required"]

    # 检查 fetch_page 工具定义
    fetch_tool = next((t for t in server.tools if t["name"] == "fetch_page"), None)
    assert fetch_tool is not None
    assert fetch_tool["description"] == "获取网页内容"
    assert "url" in fetch_tool["inputSchema"]["properties"]
    assert "url" in fetch_tool["inputSchema"]["required"]

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_initialize():
    """测试服务器初始化"""
    server = MockBaiduSearchServer()

    result = await server._initialize()

    assert "result" in result
    assert result["result"]["protocolVersion"] == "2024-11-05"
    assert result["result"]["serverInfo"]["name"] == "baidu-search"
    assert result["result"]["serverInfo"]["version"] == "0.1.0"
    assert "capabilities" in result["result"]

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_list_tools():
    """测试列出工具"""
    server = MockBaiduSearchServer()

    result = await server._list_tools()

    assert "result" in result
    tools = result["result"]["tools"]
    assert len(tools) == 2

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_search_method():
    """测试搜索方法"""
    server = MockBaiduSearchServer()

    result = await server._search("Python 异步编程", top_n=5)

    assert "result" in result
    content = result["result"]["content"][0]["text"]
    data = json.loads(content)

    assert data["query"] == "Python 异步编程"
    assert data["total"] == 3  # 模拟数据返回 3 条结果
    # 实际返回的数量应该是 min(top_n, total)
    assert len(data["results"]) == min(5, 3)  # 请求 5 条，但模拟数据只有 3 条
    assert all("title" in r for r in data["results"])
    assert all("url" in r for r in data["results"])
    assert all("snippet" in r for r in data["results"])

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_fetch_page_method():
    """测试获取页面方法"""
    server = MockBaiduSearchServer()

    result = await server._fetch_page("https://example.com/test")

    assert "result" in result
    content = result["result"]["content"][0]["text"]
    data = json.loads(content)

    assert data["url"] == "https://example.com/test"
    assert "content" in data
    assert data["length"] > 0
    assert "模拟网页内容" in data["content"]

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_call_tool_search():
    """测试调用搜索工具"""
    server = MockBaiduSearchServer()

    result = await server._call_tool("search", {"query": "测试", "top_n": 3})

    assert "result" in result

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_call_tool_fetch_page():
    """测试调用获取页面工具"""
    server = MockBaiduSearchServer()

    result = await server._call_tool("fetch_page", {"url": "https://test.com"})

    assert "result" in result

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_call_tool_unknown():
    """测试调用未知工具"""
    server = MockBaiduSearchServer()

    result = await server._call_tool("unknown_tool", {})

    assert "error" in result
    assert result["error"]["code"] == -32602

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_handle_request_initialize():
    """测试处理初始化请求"""
    server = MockBaiduSearchServer()

    result = await server.handle_request({"method": "initialize"})

    assert "result" in result

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_handle_request_list_tools():
    """测试处理列出工具请求"""
    server = MockBaiduSearchServer()

    result = await server.handle_request({"method": "tools/list"})

    assert "result" in result

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_handle_request_call_tool():
    """测试处理调用工具请求"""
    server = MockBaiduSearchServer()

    result = await server.handle_request({
        "method": "tools/call",
        "params": {
            "name": "search",
            "arguments": {"query": "test"}
        }
    })

    assert "result" in result

    server.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_baidu_search_handle_request_unknown_method():
    """测试处理未知方法请求"""
    server = MockBaiduSearchServer()

    result = await server.handle_request({"method": "unknown/method"})

    assert "error" in result
    assert result["error"]["code"] == -32601

    server.close()
