"""LLM 生成节点"""
from typing import Any, Optional

from ..state import AgentState
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("orchestrator")
logger = logger_manager.get_logger()


async def llm_generator(state: AgentState) -> AgentState:
    """LLM 生成节点 - 生成最终回答

    根据意图、工具结果等信息，使用 LLM 生成最终回答。

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态，包含最终生成的回答
    """
    from apps.orchestrator.services.llm_client import LLMClient

    client = LLMClient()
    llm = client.get_chat_model(temperature=config.get("llm.temperature", 0.7))

    # 构建提示词
    prompt = _build_prompt(state)

    try:
        response = await llm.ainvoke(prompt)
        state["final_answer"] = response.content

        # 确保 metadata 字段已初始化
        if not isinstance(state.get("metadata"), dict):
            state["metadata"] = {}
        state["metadata"]["model"] = config.get("llm.model")

        logger.info(
            f"LLM response generated for session {state['session_id']} "
            f"(intent: {state['intent']})"
        )

    except Exception as e:
        logger.error(f"Error in LLM generation: {e}")
        state["final_answer"] = "抱歉，生成回答时出现错误。请稍后重试。"

    return state


def _build_prompt(state: AgentState) -> str:
    """构建 LLM 提示词

    根据不同意图和上下文构建合适的提示词。

    Args:
        state: 当前 Agent 状态

    Returns:
        构建好的提示词字符串
    """
    intent = state.get("intent", "chat")

    if intent == "search":
        if state.get("tool_results"):
            return f"""基于以下搜索结果回答用户问题：

搜索结果：
{state['tool_results']}

用户问题：{state['user_message']}

请提供准确、有用的回答。如果搜索结果不足，可以基于你的知识补充说明。"""
        else:
            return state["user_message"]

    elif intent == "knowledge":
        if state.get("retrieved_docs"):
            docs_text = "\n\n".join(
                [doc.get("content", "") for doc in state["retrieved_docs"]]
            )
            return f"""基于以下知识库文档回答用户问题：

相关文档：
{docs_text}

用户问题：{state['user_message']}

请基于文档内容准确回答。如果文档中没有相关信息，请明确说明。"""
        else:
            return state["user_message"]

    else:  # chat
        return state["user_message"]
