"""意图识别节点"""
from typing import Any

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
    system_prompt = """你是一个精准的意图分类助手。请根据用户的输入判断最合适的意图类型：

1. search - 需要搜索互联网上的最新信息、实时新闻、天气、股价等（例如："最新新闻"、"最近发生"、"搜索"、"今天天气"等）
2. knowledge - 需要查询特定的领域知识、私有数据、文档内容或系统说明（例如："文档中关于..."、"知识库里..."、"公司的规定"、"项目架构"等）
3. chat - 通用对话、闲聊、逻辑推理、代码编写、翻译、通用行业知识或无需外部知识的一般性问题（例如："你好"、"业界通用做法"、"如何写Python"、"翻译"、"架构设计原则"等）

重要原则：
- 如果用户只是打招呼或闲聊，必须返回 'chat'。
- 如果用户询问的是通用知识、行业标准、编程问题、数学问题，即便看似专业，只要不需要查询特定的私有文档，都返回 'chat'。
- 只有当问题明显涉及特定文档、私有数据、公司内部信息或用户明确要求查知识库时，才返回 'knowledge'。
- 如果不确定，优先返回 'chat'。

只返回一个词：search、knowledge 或 chat，不要返回其他内容。"""

    user_message = (state.get("user_message") or "").strip()
    if not user_message:
        state["intent"] = "chat"
        return state

    try:
        if await _should_use_knowledge(user_message):
            state["intent"] = "knowledge"
            logger.info(f"Intent classified by KB probe: knowledge for session {state['session_id']}")
            return state
    except Exception as e:
        logger.warning(f"KB probe failed, fallback to LLM intent: {e}")

    from apps.orchestrator.services.llm_client import LLMClient

    llm_config = state.get("llm_config") or {}
    client = LLMClient(
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url")
    )
    llm = client.get_chat_model(temperature=0.1)

    try:
        full_prompt = f"{system_prompt}\n\n用户输入：{user_message}\n\n意图："

        response = await llm.ainvoke(full_prompt)
        intent = response.content.strip().lower()

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
        state["intent"] = "chat"

    return state


def _looks_like_kb_query(query: str) -> bool:
    import re

    if not query:
        return False

    lowered = query.lower()
    if "ip" in lowered or "mac" in lowered:
        return True

    if re.search(r"[\u4e00-\u9fa5]{2,4}的.*(ip|IP|mac|MAC|地址|工号|账号|权限|联系方式|邮箱|电话)", query):
        return True

    if re.search(r"(文档|知识库|制度|规定|流程|SOP|协议|架构|项目|手册|指南)", query):
        return True

    return False


def _extract_keywords(query: str) -> list:
    import re

    keywords = re.findall(r"[\u4e00-\u9fa5]{2,}|[a-zA-Z0-9]{2,}", query)
    return [k.lower() for k in keywords]


def _content_has_keywords(query: str, content: str) -> bool:
    keywords = _extract_keywords(query)
    if not keywords:
        return False
    content_lower = (content or "").lower()
    for keyword in keywords:
        if keyword in content_lower:
            return True
    return False


async def _should_use_knowledge(query: str) -> bool:
    if not _looks_like_kb_query(query):
        return False

    from apps.orchestrator.services.rag_pipeline import RAGPipelineClient

    client = RAGPipelineClient()
    try:
        results = await client.search(query, top_k=3, rerank=False)
    finally:
        await client.close()

    if not results:
        return False

    best_score = 0
    best_content = ""
    for result in results:
        score = result.get("score", 0)
        content = result.get("content", "")
        if score > best_score:
            best_score = score
            best_content = content

    if best_score >= 0.05:
        return True
    if best_score >= 0.03 and _content_has_keywords(query, best_content):
        return True
    return False
