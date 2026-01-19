"""Agent 编排图"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import (
    intent_classifier,
    skill_selector,
    llm_generator,
    tool_executor,
    rag_retriever
)


def route_after_intent(state: AgentState) -> str:
    """意图识别后的路由决策

    根据分类的意图决定下一个节点：
    - search -> skill_selector
    - knowledge -> rag_retriever
    - chat -> llm_generator

    Args:
        state: 当前 Agent 状态

    Returns:
        下一个节点的名称
    """
    intent = state.get("intent", "chat")
    if intent == "search":
        return "skill_selector"
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
    """
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("intent_classifier", intent_classifier)
    workflow.add_node("skill_selector", skill_selector)
    workflow.add_node("tool_executor", tool_executor)
    workflow.add_node("rag_retriever", rag_retriever)
    workflow.add_node("llm_generator", llm_generator)

    # 设置入口
    workflow.set_entry_point("intent_classifier")

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
