"""意图识别节点"""
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import AgentState
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("orchestrator")
logger = logger_manager.get_logger()


async def intent_classifier(state: AgentState) -> AgentState:
    """意图识别节点 - 使用 LLM 判断用户意图

    判断用户的意图类型：
    - search: 需要搜索最新信息
    - knowledge: 需要查询知识库
    - chat: 普通对话

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态，包含分类的意图
    """
    system_prompt = """你是一个意图分类助手。判断用户的意图类型：

1. search - 需要搜索最新信息（例如："最新新闻"、"最近发生"、"搜索"等）
2. knowledge - 需要查询知识库（例如："文档内容"、"知识库中"、"系统说明"等）
3. chat - 普通对话（例如："你好"、"谢谢"、"是什么意思"等）

只返回一个词：search、knowledge 或 chat，不要返回其他内容。"""

    # 使用 SimpleLLMClient
    from apps.orchestrator.services.simple_llm_client import SimpleLLMClient

    client = SimpleLLMClient()

    try:
        # 构建完整提示
        full_prompt = f"{system_prompt}\n\n用户输入：{state['user_message']}\n\n意图："

        response = await client.achat([full_prompt], temperature=0.1)
        intent = response.strip().lower()

        # 验证并设置意图
        valid_intents = ["search", "knowledge", "chat"]
        if intent not in valid_intents:
            logger.warning(
                f"Invalid intent '{intent}' detected, defaulting to 'chat'"
            )
            intent = "chat"

        state["intent"] = intent
        logger.info(f"Intent classified: {intent} for session {state['session_id']}")

    except Exception as e:
        logger.error(f"Error in intent classification: {e}")
        # 出错时默认为 chat
        state["intent"] = "chat"

    return state
