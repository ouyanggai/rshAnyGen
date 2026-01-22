"""Agent 编排图"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import (
    entry_router,
    rag_checker,
    intent_classifier,
    skill_selector,
    llm_generator,
    tool_executor,
    rag_retriever
)


def route_after_rag_check(state: AgentState) -> str:
    """RAG 检查后的路由决策
    
    Deprecated or used for implicit RAG?
    For Multi-KB, we check kb_ids in intent or earlier.
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
    - kb_ids (用户明确选择) -> rag_retriever
    - search + 启用搜索 -> skill_selector
    - search + 未启用搜索 -> llm_generator（跳过搜索）
    - knowledge -> rag_retriever
    - chat -> llm_generator

    Args:
        state: 当前 Agent 状态

    Returns:
        下一个节点的名称
    """
    kb_ids = state.get("kb_ids", [])
    if kb_ids:
        # 如果用户选择了知识库，优先查询知识库
        return "rag_retriever"

    intent = state.get("intent", "chat")
    enable_search = state.get("enable_search", False)

    if intent == "search":
        if enable_search:
            return "skill_selector"
        else:
            # 用户关闭了搜索，直接对话
            return "llm_generator"
    elif intent == "knowledge":
        # 即使没有kb_ids，如果意图是knowledge，可能是默认知识库？
        # 目前设计文档说 "未选择知识库时，系统使用纯聊天模式"
        # 但如果意图检测器认为需要知识库（比如 "介绍一下项目"），可能需要 fallback 或提示
        # 这里暂时保留原有逻辑，或者直接去 llm_generator
        return "llm_generator" # 既然设计说未选择就是纯聊天
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
    """
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("entry_router", entry_router)
    workflow.add_node("rag_checker", rag_checker)
    workflow.add_node("intent_classifier", intent_classifier)
    workflow.add_node("skill_selector", skill_selector)
    workflow.add_node("tool_executor", tool_executor)
    workflow.add_node("rag_retriever", rag_retriever)
    workflow.add_node("llm_generator", llm_generator)

    workflow.set_entry_point("entry_router")

    def _route_after_entry(state: AgentState) -> str:
        kb_ids = state.get("kb_ids", [])
        if kb_ids:
            return "rag_retriever"
        return "intent_classifier"

    workflow.add_conditional_edges(
        "entry_router",
        _route_after_entry,
        {
            "intent_classifier": "intent_classifier",
            "rag_retriever": "rag_retriever",
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
