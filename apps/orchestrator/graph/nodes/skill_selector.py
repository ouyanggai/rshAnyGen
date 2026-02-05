"""技能选择节点"""
from typing import Any, Optional, List

from ..state import AgentState
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from apps.orchestrator.services.skill_registry import SkillsRegistryClient

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


DEFAULT_SKILL_MAPPING = {
    "search": "web_search",
    "knowledge": "knowledge_query",
}


def _pick_search_skill(skills: List[dict]) -> Optional[str]:
    if not skills:
        return None
    for s in skills:
        if (s.get("category") == "search") or ("search" in (s.get("id") or "").lower()):
            return s.get("id")
    return None


async def _select_skill_with_llm(user_message: str, skills: List[dict]) -> Optional[str]:
    if not skills:
        return None
    from apps.orchestrator.services.llm_client import LLMClient

    llm = LLMClient().get_chat_model(temperature=0.1)
    skills_desc = "\n".join(
        [
            f"- {s.get('id')}: {s.get('title') or s.get('id')} ({s.get('description') or '无描述'})"
            for s in skills
        ]
    )
    prompt = f"""你是技能路由器。根据用户请求选择最合适的技能ID。
如果没有合适技能，返回 "none"。

可用技能:
{skills_desc}

用户请求: {user_message}

只输出 JSON:
{{"skill":"skill_id_or_none"}}"""

    try:
        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        import json
        data = json.loads(raw.strip())
        skill_id = (data.get("skill") or "").strip()
        if not skill_id or skill_id.lower() == "none":
            return None
        return skill_id
    except Exception as e:
        logger.warning(f"LLM skill selection failed: {e}")
        return None


async def skill_selector(state: AgentState) -> AgentState:
    """技能选择节点 - 根据意图选择合适的技能

    根据意图分类结果，选择对应的技能来处理用户请求。

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态，包含选定的技能和参数
    """
    intent = state.get("intent", "chat")

    # 拉取技能列表
    skills: List[dict] = []
    client = SkillsRegistryClient()
    try:
        data = await client.list_skills()
        skills = [s for s in data.get("skills", []) if s.get("enabled", True)]
    except Exception as e:
        logger.warning(f"Failed to list skills: {e}")
    finally:
        await client.close()

    # 默认选择
    selected_skill = None

    if intent == "search":
        selected_skill = _pick_search_skill(skills) or DEFAULT_SKILL_MAPPING.get(intent)
    elif intent == "knowledge":
        selected_skill = DEFAULT_SKILL_MAPPING.get(intent)
    else:
        # 普通对话尝试智能选择技能（避免把“通用对话”当成外部工具调用，避免重复/降级）
        filtered = [s for s in skills if (s.get("id") != "general_chat")]
        selected_skill = await _select_skill_with_llm(state.get("user_message", ""), filtered)

    # 准备技能参数
    skill_parameters = None

    if selected_skill:
        # 参数尽量保持“技能专用”，上下文信息走 tool_executor 的 context 字段
        user_text = state.get("user_message", "")

        if selected_skill == "text_summary":
            skill_parameters = {"text": user_text}
        elif selected_skill in ("general_chat",):
            skill_parameters = {"message": user_text}
        else:
            # 默认参数名：query
            skill_parameters = {"query": user_text}

    # 根据不同技能添加特定参数
        if intent == "search":
            skill_parameters.update(
                {
                    "search_type": "web",
                    "top_n": _get_validated_config(
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
