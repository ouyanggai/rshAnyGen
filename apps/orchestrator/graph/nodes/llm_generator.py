"""LLM 生成节点"""

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

    llm_config = state.get("llm_config") or {}
    client = LLMClient(
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url")
    )
    llm = client.get_chat_model(temperature=config.get("llm.temperature", 0.7))

    # 构建提示词
    prompt = _build_prompt(state)

    try:
        response = await llm.ainvoke(
            prompt,
            config={"tags": ["final_answer"]}
        )
        state["final_answer"] = response.content

        # 确保 metadata 字段已初始化
        if not isinstance(state.get("metadata"), dict):
            state["metadata"] = {}
        model_name = getattr(llm, "model_name", None) or getattr(llm, "model", None) or "unknown"
        state["metadata"]["model"] = model_name

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
    user_message = state["user_message"]
    retrieved_docs = state.get("retrieved_docs", [])
    tool_results = state.get("tool_results")
    messages = state.get("messages") or []

    history_lines = []
    for m in messages:
        if isinstance(m, dict):
            role = m.get("role")
            content = m.get("content")
        else:
            role = getattr(m, "role", None)
            content = getattr(m, "content", None)
        if not role or not content:
            continue
        history_lines.append(f"{role}: {content}")

    if history_lines and history_lines[-1] == f"user: {user_message}":
        history_lines = history_lines[:-1]
    history_text = "\n".join(history_lines[-40:]) if history_lines else ""

    # 有知识库内容的情况（严谨模式）
    if retrieved_docs:
        # 打印检索到的文档内容到控制台，以便调试
        logger.info(f"\n=== Vector Store Retrieval Result (Session: {state.get('session_id')}) ===")
        for i, doc in enumerate(retrieved_docs):
            logger.info(f"Doc {i+1} [Score: {doc.get('score', 0):.4f}]:\nContent: {doc.get('content', '')}\nMetadata: {doc.get('metadata', {})}")
        logger.info("==============================================================\n")

        docs_text = "\n\n---\n\n".join([
            f"[相关度: {doc.get('score', 0):.2f}]\n{doc.get('content', '')}"
            for doc in retrieved_docs
        ])

        return f"""你是一个专业、乐于助人的 AI 助手。请基于以下知识库内容回答用户问题。

=== 对话上下文 ===
{history_text if history_text else "（无）"}

=== 知识库内容 ===
{docs_text}

=== 用户问题 ===
{user_message}

=== 回答要求 ===
1. 保持专业、客观、有条理的回答风格。
2. 请使用 Markdown 格式进行排版（如标题、列表、代码块等）。
3. 仔细分析用户意图，只回答相关信息（如只问"XX是谁"则不提供IP/MAC）。
4. 严格基于知识库内容回答。
5. 如果知识库完全没有相关信息，请直接说明："根据现有知识库，我无法找到关于该问题的相关信息。"
6. 不要列出无关的元数据或所有细节，除非用户明确要求。
"""

    # 无知识库内容的情况（通用闲聊）
    elif intent == "search" and tool_results:
        return f"""你是一个智能助手。基于以下搜索结果回答用户问题。
=== 对话上下文 ===
{history_text if history_text else "（无）"}

=== 搜索结果 ===
{tool_results}
=== 用户问题 ===
{user_message}

=== 回答要求 ===
1. 先理解用户真正想知道什么，只回答相关信息
2. 基于搜索结果提供准确、有用的回答
3. 如果搜索结果不足，可以适当补充说明，但明确区分哪些是搜索结果，哪些是你的补充
4. 保持客观、中立、专业

现在请回答："""

    else:
        return f"""你是一个专业、严谨的 AI 助手。

=== 对话上下文 ===
{history_text if history_text else "（无）"}
    
=== 用户问题 ===
{user_message}

=== 回答要求 ===
1. 请用专业、客观、简洁的风格回答用户的问题。
2. 严禁使用俏皮、卖萌、幽默或过于口语化的表达。
3. 如果问题需要具体事实而你不知道，请诚实说明。
4. 直接回答问题，不要有多余的废话。
"""
