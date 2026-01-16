"""技能选择节点"""
from typing import Any, Optional

from ..state import AgentState
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("orchestrator")
logger = logger_manager.get_logger()


def _get_validated_config(key: str, default: Any, expected_type: type) -> Any:
    """验证并返回配置值

    Args:
        key: 配置键
        default: 默认值
        expected_type: 期望的类型

    Returns:
        验证后的配置值
    """
    value = config.get(key, default)
    if not isinstance(value, expected_type):
        logger.warning(
            f"Invalid config {key}: {value}, using default {default}"
        )
        return default
    return value


# 技能映射配置
SKILL_MAPPING = {
    "search": "web_search",
    "knowledge": "rag_query",
    "chat": "general_chat",
}


async def skill_selector(state: AgentState) -> AgentState:
    """技能选择节点 - 根据意图选择合适的技能

    根据意图分类结果，选择对应的技能来处理用户请求。

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态，包含选定的技能和参数
    """
    intent = state.get("intent", "chat")

    # 根据意图映射到技能
    selected_skill = SKILL_MAPPING.get(intent, "general_chat")

    # 准备技能参数
    skill_parameters = {
        "query": state["user_message"],
        "intent": intent,
        "session_id": state["session_id"],
    }

    # 根据不同技能添加特定参数
    if intent == "search":
        skill_parameters.update(
            {
                "search_type": "web",
                "max_results": _get_validated_config(
                    "tools.web_search.max_results", 5, int
                ),
            }
        )
    elif intent == "knowledge":
        skill_parameters.update(
            {
                "retrieval_type": "vector",
                "top_k": _get_validated_config(
                    "rag.retrieval.top_k", 3, int
                ),
            }
        )

    state["selected_skill"] = selected_skill
    state["skill_parameters"] = skill_parameters

    logger.info(
        f"Skill selected: {selected_skill} for intent {intent} "
        f"(session: {state['session_id']})"
    )

    return state
