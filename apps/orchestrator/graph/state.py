"""Agent 状态定义"""
from typing import List, Optional, Any
from langgraph.graph import MessagesState
from typing_extensions import TypedDict


class AgentState(MessagesState):
    """Agent 状态定义

    继承自 LangGraph 的 MessagesState，包含聊天历史
    """

    # 输入
    session_id: str
    user_message: str
    # chat_history 由 MessagesState 提供

    # 中间状态
    intent: str  # "search" | "knowledge" | "chat"
    selected_skill: Optional[str] = None
    skill_parameters: Optional[dict] = None
    tool_call_approved: bool = True

    # RAG 相关
    retrieved_docs: List[dict]
    reranked_docs: List[dict]

    # 工具相关
    tool_results: Optional[Any] = None

    # 输出
    final_answer: str
    citations: List[dict]
    metadata: dict
