"""Agent 编排图"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import (
    rag_checker,
    intent_classifier,
    skill_selector,
    llm_generator,
    tool_executor,
    rag_retriever
)


def route_after_rag_check(state: AgentState) -> str:
    """RAG 检查后的路由决策

    优先使用知识库：
    - 有相关内容 -> rag_retriever（完整检索）
    - 无相关内容 -> 检查是否启用搜索
        - 启用搜索 -> intent_classifier
        - 未启用搜索 -> llm_generator（直接对话）

    Args:
        state: 当前 Agent 状态

    Returns:
        下一个节点的名称
    """
    if state.get("rag_has_relevant", False):
        return "rag_retriever"
    else:
        # 知识库没有相关内容
        if state.get("enable_search", False):
            # 用户启用了搜索，进行意图分类
            return "intent_classifier"
        else:
            # 用户未启用搜索，直接对话（不用联网搜索）
            return "llm_generator"


def route_after_intent(state: AgentState) -> str:
    """意图识别后的路由决策

    根据分类的意图和搜索开关决定下一个节点：
    - search + 启用搜索 -> skill_selector
    - search + 未启用搜索 -> llm_generator（跳过搜索）
    - knowledge -> rag_retriever
    - chat -> llm_generator

    Args:
        state: 当前 Agent 状态

    Returns:
        下一个节点的名称
    """
    intent = state.get("intent", "chat")
    enable_search = state.get("enable_search", False)

    if intent == "search":
        if enable_search:
            return "skill_selector"
        else:
            # 用户关闭了搜索，直接对话
            return "llm_generator"
    elif intent == "knowledge":
        return "rag_retriever"
    else:
        # chat or unknown
        return "llm_generator"


def check_tool_approval(state: AgentState) -> str:
    """检查工具调用是否获得批准"""
    if state.get("tool_call_approved", True):
        return "tool_executor"
    return "llm_generator"  # Skip execution if not approved, let LLM explain or handle


def create_agent_graph():
    """创建 Agent 编排图

    构建完整的 LangGraph 工作流

    新的流程：
    1. rag_checker - 快速检查知识库
    2. 如果有相关内容 -> rag_retriever
    3. 如果无相关内容 -> intent_classifier -> skill_selector/tool_executor 或 llm_generator
    """
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("rag_checker", rag_checker)
    workflow.add_node("intent_classifier", intent_classifier)
    workflow.add_node("skill_selector", skill_selector)
    workflow.add_node("tool_executor", tool_executor)
    workflow.add_node("rag_retriever", rag_retriever)
    workflow.add_node("llm_generator", llm_generator)

    # 设置入口为 intent_classifier，优先进行意图识别，避免不必要的 RAG 查询
    workflow.set_entry_point("intent_classifier")

    # RAG 检查后的条件边 (保留但暂时不作为入口)
    def _route_after_rag_check(state: AgentState) -> str:
        return route_after_rag_check(state)

    workflow.add_conditional_edges(
        "rag_checker",
        _route_after_rag_check,
        {
            "rag_retriever": "rag_retriever",
            "intent_classifier": "intent_classifier",
        },
    )

    # 添加条件边：意图识别 -> 分支
    def _route_after_intent(state: AgentState) -> str:
        return route_after_intent(state)

    workflow.add_conditional_edges(
        "intent_classifier",
        _route_after_intent,
        {
            "skill_selector": "skill_selector",
            "rag_retriever": "rag_retriever",
            "llm_generator": "llm_generator",
        },
    )

    # 搜索分支：技能选择 -> 工具执行 -> LLM
    # 这里可以添加审批逻辑，暂时直接连接
    workflow.add_edge("skill_selector", "tool_executor")
    workflow.add_edge("tool_executor", "llm_generator")

    # RAG 分支：检索 -> LLM
    workflow.add_edge("rag_retriever", "llm_generator")

    # LLM 生成后结束
    workflow.add_edge("llm_generator", END)

    # 编译图（带内存检查点）
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def get_graph_visualization():
    """获取图的可视化表示"""
    graph = create_agent_graph()
    return graph.get_graph().print_ascii()
