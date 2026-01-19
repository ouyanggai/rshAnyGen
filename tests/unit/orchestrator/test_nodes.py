"""测试 Orchestrator 图节点"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from apps.orchestrator.graph.state import AgentState
from apps.orchestrator.graph.nodes import (
    intent_classifier,
    skill_selector,
    llm_generator,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_intent_classifier_search():
    """测试意图识别 - 搜索意图"""
    state = AgentState(
        session_id="test-001",
        user_message="帮我搜索最新的 AI 新闻",
        messages=[],
        intent="",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    # Mock LLM 响应
    mock_response = MagicMock()
    mock_response.content = "search"

    # Mock the ChatOpenAI instance that get_chat_model returns
    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await intent_classifier(state)

        assert result["intent"] == "search"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_intent_classifier_knowledge():
    """测试意图识别 - 知识库意图"""
    state = AgentState(
        session_id="test-002",
        user_message="查询知识库中的文档",
        messages=[],
        intent="",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    mock_response = MagicMock()
    mock_response.content = "knowledge"

    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await intent_classifier(state)

        assert result["intent"] == "knowledge"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_intent_classifier_chat():
    """测试意图识别 - 普通对话意图"""
    state = AgentState(
        session_id="test-003",
        user_message="你好，很高兴认识你",
        messages=[],
        intent="",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    mock_response = MagicMock()
    mock_response.content = "chat"

    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await intent_classifier(state)

        assert result["intent"] == "chat"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_intent_classifier_invalid_intent():
    """测试意图识别 - 无效意图默认为 chat"""
    state = AgentState(
        session_id="test-004",
        user_message="测试消息",
        messages=[],
        intent="",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    mock_response = MagicMock()
    mock_response.content = "invalid_intent"

    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await intent_classifier(state)

        assert result["intent"] == "chat"  # 默认值


@pytest.mark.unit
@pytest.mark.asyncio
async def test_intent_classifier_error_handling():
    """测试意图识别 - 错误处理"""
    state = AgentState(
        session_id="test-005",
        user_message="测试消息",
        messages=[],
        intent="",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await intent_classifier(state)

        assert result["intent"] == "chat"  # 错误时默认为 chat


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skill_selector_search():
    """测试技能选择 - 搜索意图"""
    state = AgentState(
        session_id="test-006",
        user_message="搜索 AI 新闻",
        messages=[],
        intent="search",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    result = await skill_selector(state)

    assert result["selected_skill"] == "web_search"
    assert result["skill_parameters"]["intent"] == "search"
    assert result["skill_parameters"]["query"] == "搜索 AI 新闻"
    assert result["skill_parameters"]["search_type"] == "web"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skill_selector_knowledge():
    """测试技能选择 - 知识库意图"""
    state = AgentState(
        session_id="test-007",
        user_message="查询文档",
        messages=[],
        intent="knowledge",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    result = await skill_selector(state)

    assert result["selected_skill"] == "rag_query"
    assert result["skill_parameters"]["intent"] == "knowledge"
    assert result["skill_parameters"]["retrieval_type"] == "vector"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skill_selector_chat():
    """测试技能选择 - 普通对话意图"""
    state = AgentState(
        session_id="test-008",
        user_message="你好",
        messages=[],
        intent="chat",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    result = await skill_selector(state)

    assert result["selected_skill"] == "general_chat"
    assert result["skill_parameters"]["intent"] == "chat"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skill_selector_default():
    """测试技能选择 - 未知意图默认处理"""
    state = AgentState(
        session_id="test-009",
        user_message="测试",
        messages=[],
        intent="unknown",  # 未知意图
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    result = await skill_selector(state)

    assert result["selected_skill"] == "general_chat"  # 默认技能


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_generator_chat():
    """测试 LLM 生成 - 普通对话"""
    state = AgentState(
        session_id="test-010",
        user_message="你好，请介绍一下你自己",
        messages=[],
        intent="chat",
        selected_skill="general_chat",
        skill_parameters={},
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    mock_response = MagicMock()
    mock_response.content = "你好！我是 AI 助手，很高兴为您服务。"

    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await llm_generator(state)

        assert result["final_answer"] == "你好！我是 AI 助手，很高兴为您服务。"
        assert result["metadata"]["model"] is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_generator_search_with_results():
    """测试 LLM 生成 - 带搜索结果"""
    state = AgentState(
        session_id="test-011",
        user_message="最新的 AI 技术进展",
        messages=[],
        intent="search",
        selected_skill="web_search",
        skill_parameters={},
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results="找到 5 篇相关文章：1. GPT-5 发布... 2. Claude 4 发布...",
        final_answer="",
        citations=[],
        metadata={},
    )

    mock_response = MagicMock()
    mock_response.content = "根据搜索结果，最新的 AI 技术进展包括..."

    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await llm_generator(state)

        assert result["final_answer"] == "根据搜索结果，最新的 AI 技术进展包括..."
        # 验证 prompt 包含搜索结果
        call_args = mock_llm_instance.ainvoke.call_args[0][0]
        assert "搜索结果" in call_args


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_generator_knowledge_with_docs():
    """测试 LLM 生成 - 带知识库文档"""
    state = AgentState(
        session_id="test-012",
        user_message="系统的架构是怎样的？",
        messages=[],
        intent="knowledge",
        selected_skill="rag_query",
        skill_parameters={},
        tool_call_approved=True,
        retrieved_docs=[
            {"content": "系统采用微服务架构..."},
            {"content": "包含以下模块：Orchestrator、RAG、Tools..."},
        ],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    mock_response = MagicMock()
    mock_response.content = "根据知识库文档，系统架构如下..."

    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await llm_generator(state)

        assert result["final_answer"] == "根据知识库文档，系统架构如下..."
        # 验证 prompt 包含文档内容
        call_args = mock_llm_instance.ainvoke.call_args[0][0]
        assert "知识库文档" in call_args


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_generator_error_handling():
    """测试 LLM 生成 - 错误处理"""
    state = AgentState(
        session_id="test-013",
        user_message="测试",
        messages=[],
        intent="chat",
        selected_skill="general_chat",
        skill_parameters={},
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await llm_generator(state)

        assert result["final_answer"] == "抱歉，生成回答时出现错误。请稍后重试。"


@pytest.mark.unit
def test_build_prompt_chat():
    """测试提示词构建 - 普通对话"""
    from apps.orchestrator.graph.nodes.llm_generator import _build_prompt

    state = AgentState(
        session_id="test",
        user_message="你好",
        messages=[],
        intent="chat",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    prompt = _build_prompt(state)
    assert prompt == "你好"


@pytest.mark.unit
def test_build_prompt_search_with_results():
    """测试提示词构建 - 搜索结果"""
    from apps.orchestrator.graph.nodes.llm_generator import _build_prompt

    state = AgentState(
        session_id="test",
        user_message="搜索 AI",
        messages=[],
        intent="search",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results="找到一些结果",
        final_answer="",
        citations=[],
        metadata={},
    )

    prompt = _build_prompt(state)
    assert "搜索结果" in prompt
    assert "找到一些结果" in prompt
    assert "搜索 AI" in prompt


@pytest.mark.unit
def test_build_prompt_search_no_results():
    """测试提示词构建 - 搜索无结果"""
    from apps.orchestrator.graph.nodes.llm_generator import _build_prompt

    state = AgentState(
        session_id="test",
        user_message="搜索 AI",
        messages=[],
        intent="search",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    prompt = _build_prompt(state)
    assert prompt == "搜索 AI"


@pytest.mark.unit
def test_build_prompt_knowledge_with_docs():
    """测试提示词构建 - 知识库文档"""
    from apps.orchestrator.graph.nodes.llm_generator import _build_prompt

    state = AgentState(
        session_id="test",
        user_message="系统架构",
        messages=[],
        intent="knowledge",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[{"content": "文档内容"}],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    prompt = _build_prompt(state)
    assert "知识库文档" in prompt
    assert "文档内容" in prompt


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_generator_metadata_init():
    """测试：metadata 字段初始化"""
    from apps.orchestrator.graph.nodes.llm_generator import llm_generator

    state = AgentState(
        session_id="test-014",
        user_message="test",
        messages=[],
        intent="chat"
        # 故意不设置 metadata
    )

    mock_response = MagicMock()
    mock_response.content = "测试响应"

    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await llm_generator(state)

        # 验证 metadata 被正确初始化
        assert isinstance(result["metadata"], dict)
        assert "model" in result["metadata"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_generator_metadata_existing():
    """测试：metadata 字段已存在时的处理"""
    from apps.orchestrator.graph.nodes.llm_generator import llm_generator

    state = AgentState(
        session_id="test-015",
        user_message="test",
        messages=[],
        intent="chat",
        metadata={"existing_key": "existing_value"}
    )

    mock_response = MagicMock()
    mock_response.content = "测试响应"

    mock_llm_instance = MagicMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)

    with patch("apps.orchestrator.services.llm_client.ChatOpenAI", return_value=mock_llm_instance):
        result = await llm_generator(state)

        # 验证现有 metadata 被保留且新增 model 字段
        assert isinstance(result["metadata"], dict)
        assert "model" in result["metadata"]
        assert result["metadata"]["existing_key"] == "existing_value"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skill_selector_invalid_config():
    """测试：配置值验证 - 无效配置使用默认值"""
    from apps.orchestrator.graph.nodes.skill_selector import skill_selector

    state = AgentState(
        session_id="test-016",
        user_message="搜索",
        messages=[],
        intent="search",
        selected_skill=None,
        skill_parameters=None,
        tool_call_approved=True,
        retrieved_docs=[],
        reranked_docs=[],
        tool_results=None,
        final_answer="",
        citations=[],
        metadata={},
    )

    # Mock config 返回无效类型
    with patch(
        "apps.orchestrator.graph.nodes.skill_selector.config.get"
    ) as mock_config:
        # 第一次调用返回无效类型（字符串而非整数）
        mock_config.side_effect = lambda key, default: "invalid" if key == "tools.web_search.max_results" else default

        result = await skill_selector(state)

        # 验证使用了默认值 5
        assert result["skill_parameters"]["max_results"] == 5
