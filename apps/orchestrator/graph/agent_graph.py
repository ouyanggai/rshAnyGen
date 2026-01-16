"""Agent 编排图"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import (
    intent_classifier,
    skill_selector,
    llm_generator,
)


def route_after_intent(state: AgentState) -> str:
    """意图识别后的路由决策

    根据分类的意图决定下一个节点：
    - search/knowledge -> skill_selector
    - chat -> llm_generator

    Args:
        state: 当前 Agent 状态

    Returns:
        下一个节点的名称
    """
    intent = state.get("intent", "chat")
    if intent in ["search", "knowledge"]:
        # 需要工具技能，先选择技能
        return "skill_selector"
    else:
        # 普通对话，直接生成
        return "llm_generator"


def create_agent_graph():
    """创建 Agent 编排图

    构建完整的 LangGraph 工作流，包含以下节点：
    1. intent_classifier - 意图识别
    2. skill_selector - 技能选择
    3. llm_generator - LLM 生成

    Returns:
        编译后的 LangGraph 实例，带内存检查点
    """
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("intent_classifier", intent_classifier)
    workflow.add_node("skill_selector", skill_selector)
    workflow.add_node("llm_generator", llm_generator)

    # 设置入口
    workflow.set_entry_point("intent_classifier")

    # 添加条件边（使用内部路由函数）
    def _route_after_intent(state: AgentState) -> str:
        return route_after_intent(state)

    workflow.add_conditional_edges(
        "intent_classifier",
        _route_after_intent,
        {
            "skill_selector": "skill_selector",
            "llm_generator": "llm_generator",
        },
    )

    # 技能选择后统一进入 LLM 生成
    workflow.add_edge("skill_selector", "llm_generator")

    # LLM 生成后结束
    workflow.add_edge("llm_generator", END)

    # 编译图（带内存检查点）
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def get_graph_visualization():
    """获取图的可视化表示

    Returns:
        图的 ASCII 艺术表示或 Mermaid 格式
    """
    graph = create_agent_graph()
    return graph.get_graph().print_ascii()
