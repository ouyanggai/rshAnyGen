"""Agent 状态测试"""
import pytest
from apps.orchestrator.graph.state import AgentState


@pytest.mark.unit
def test_agent_state_initialization():
    """测试：Agent 状态初始化"""
    state = AgentState(
        session_id="sess-123",
        user_message="你好",
        messages=[],
        intent="",  # 必需字段
        retrieved_docs=[],  # 必需字段
        reranked_docs=[],  # 必需字段
        final_answer="",  # 必需字段
        citations=[],  # 必需字段
        metadata={},  # 必需字段
    )

    assert state["session_id"] == "sess-123"
    assert state["user_message"] == "你好"
    assert state["intent"] == ""  # 默认空字符串
    # 注意：tool_call_approved 有默认值，但如果未提供则不存在于字典中
    # 这是 TypedDict 的特性


@pytest.mark.unit
def test_agent_state_with_rag():
    """测试：带 RAG 的状态"""
    state = AgentState(
        session_id="sess-123",
        user_message="搜索最新的 AI 新闻",
        messages=[],
        intent="search",
        retrieved_docs=[{"title": "新闻1", "content": "..."}],
        reranked_docs=[],
        final_answer="",
        citations=[],
        metadata={},
    )

    assert state["intent"] == "search"
    assert len(state["retrieved_docs"]) == 1
    assert state["final_answer"] == ""


@pytest.mark.unit
def test_agent_state_with_skill_selection():
    """测试：技能选择状态"""
    state = AgentState(
        session_id="sess-456",
        user_message="帮我搜索天气",
        messages=[],
        intent="search",
        selected_skill="web_search",
        skill_parameters={"query": "天气", "num_results": 5},
        retrieved_docs=[],
        reranked_docs=[],
        final_answer="",
        citations=[],
        metadata={},
    )

    assert state["intent"] == "search"
    assert state["selected_skill"] == "web_search"
    assert state["skill_parameters"]["num_results"] == 5


@pytest.mark.unit
def test_agent_state_with_reranked_docs():
    """测试：重排序文档状态"""
    state = AgentState(
        session_id="sess-789",
        user_message="查询文档",
        messages=[],
        retrieved_docs=[
            {"title": "Doc1", "score": 0.8},
            {"title": "Doc2", "score": 0.6}
        ],
        reranked_docs=[
            {"title": "Doc1", "score": 0.9},
            {"title": "Doc2", "score": 0.7}
        ]
    )

    assert len(state["retrieved_docs"]) == 2
    assert len(state["reranked_docs"]) == 2
    assert state["reranked_docs"][0]["score"] == 0.9


@pytest.mark.unit
def test_agent_state_final_answer():
    """测试：最终答案状态"""
    state = AgentState(
        session_id="sess-999",
        user_message="问题",
        messages=[],
        final_answer="这是答案",
        citations=[{"source": "doc1", "page": 1}],
        metadata={"model": "gpt-4", "tokens": 100}
    )

    assert state["final_answer"] == "这是答案"
    assert len(state["citations"]) == 1
    assert state["metadata"]["model"] == "gpt-4"


@pytest.mark.unit
def test_agent_state_tool_rejection():
    """测试：工具调用拒绝状态"""
    state = AgentState(
        session_id="sess-000",
        user_message="删除文件",
        messages=[],
        tool_call_approved=False
    )

    assert state["tool_call_approved"] is False
