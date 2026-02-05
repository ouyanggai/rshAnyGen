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
        # 添加详细日志记录
        logger.info(f"=== LLM Prompt for session {state['session_id']} ===")
        logger.info(f"Prompt length: {len(prompt)} characters")
        logger.info(f"Prompt content:\n{prompt}")
        logger.info("=" * 60)

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
        logger.info(f"LLM response content:\n{response.content}")

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
    system_contexts = []  # 收集系统上下文

    for m in messages:
        if isinstance(m, dict):
            role = m.get("role")
            content = m.get("content")
        else:
            role = getattr(m, "role", None)
            content = getattr(m, "content", None)

        if not role or not content:
            continue

        # 特殊处理system消息
        if role == "system":
            # 将system消息收集到系统上下文中
            system_contexts.append(content)
        else:
            # 对话消息
            if role in ["user", "assistant"]:
                history_lines.append(f"{role}: {content}")

    if history_lines and history_lines[-1] == f"user: {user_message}":
        history_lines = history_lines[:-1]

    history_text = "\n".join(history_lines[-40:]) if history_lines else ""
    system_text = "\n".join(system_contexts) if system_contexts else ""

    # 有知识库内容的情况（企业RAG问答）
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

        return f"""# 润世华集团企业AI助手

## 身份定位
你是一个专业的企业级AI助手，服务于润世华集团及其各子公司。你拥有公司内部的RAG知识库访问权限，能够基于企业知识为员工提供准确、专业的回答。

## 系统上下文（用户信息）
{system_text if system_text else "（无）"}

## 对话上下文
{history_text if history_text else "（无）"}

## 知识库内容（内部资料）
{docs_text}

## 用户问题
{user_message}

## 回答规范
### 回答风格
- **企业级专业性**：使用正式、准确的商业语言
- **结构化表达**：采用层次分明的回答结构
- **基于证据**：所有回答必须严格基于提供的知识库内容
- **Markdown格式**：合理使用标题、列表、表格、代码块等格式

### 核心要求
1. **身份识别优先**：首先确认并提及用户身份，体现个性化服务
2. **精准回答**：严格围绕问题核心，避免冗余信息
3. **来源标注**：适当引用知识库中的具体内容作为依据
4. **知识边界**：如果知识库无相关内容，明确说明并建议其他咨询渠道
5. **保密意识**：不输出超出权限范围的信息

### 禁止事项
- 避免使用俏皮、幽默或过于口语化的表达
- 不臆测或编造知识库外的信息
- 不泄露其他用户的隐私信息
- 不提供涉及商业机密或敏感数据的内容

现在请基于以上规范回答用户问题。"""

    # 搜索场景（联网搜索）
    elif intent == "search" and tool_results:
        return f"""# 润世华集团企业AI助手 - 搜索模式

## 身份定位
你是一个专业的企业级AI助手，正在为润世华集团员工提供基于联网搜索的信息咨询服务。

## 系统上下文（用户信息）
{system_text if system_text else "（无）"}

## 对话上下文
{history_text if history_text else "（无）"}

## 搜索结果（来自互联网）
{tool_results}

## 用户问题
{user_message}

## 回答规范
### 回答风格
- **企业级专业性**：保持正式、准确的商业沟通风格
- **信息透明**：明确标注哪些信息来自搜索结果，哪些是你的补充说明
- **结构化呈现**：使用清晰的层次结构和格式

### 核心要求
1. **身份确认**：首先确认用户身份，体现个性化服务
2. **信息整合**：
   - 基于搜索结果提供准确回答
   - 对搜索结果进行适当分析和总结
   - 明确区分"搜索结果"和"AI分析"
3. **客观中性**：保持信息呈现的客观性，避免主观判断
4. **时效意识**：注意信息的时效性，必要时提醒用户
5. **实用导向**：提供对工作或业务有实际价值的建议

### 注意事项
- 搜索结果可能不完全准确，需要理性参考
- 对于重要决策，建议用户进一步核实信息
- 不泄露企业内部敏感信息
- 保持专业、礼貌的服务态度

现在请基于以上规范回答用户问题。"""

    # 工具结果场景（非搜索）
    elif tool_results:
        return f"""# 润世华集团企业AI助手 - 工具增强

## 身份定位
你是一个专业的企业级AI助手，当前已调用外部技能/工具获取结果，请基于工具结果回答。

## 系统上下文（用户信息）
{system_text if system_text else "（无）"}

## 对话上下文
{history_text if history_text else "（无）"}

## 工具结果
{tool_results}

## 用户问题
{user_message}

## 回答规范
### 回答风格
- **企业级专业性**：使用正式、准确的商业语言
- **结构清晰**：使用分点/步骤/表格等方式清晰表达
- **以工具结果为依据**：明确基于工具结果作答

### 核心要求
1. 如工具结果不足以回答，说明不足并给出下一步建议
2. 不臆测工具结果之外的信息
3. 对关键结论进行简短总结

现在请基于以上规范回答用户问题。"""

    # 通用日常问答（无知识库、无搜索）
    else:
        return f"""# 润世华集团企业AI助手 - 日常咨询

## 身份定位
你是一个专业的企业级AI助手，服务于润世华集团及其各子公司。你专注于为企业员工提供日常工作和生活中的咨询建议。

## 系统上下文（用户信息）
{system_text if system_text else "（无）"}

## 对话上下文
{history_text if history_text else "（无）"}

## 用户问题
{user_message}

## 回答规范
### 回答风格
- **企业级专业性**：使用正式、准确、简洁的商业语言
- **服务导向**：以解决用户实际需求为核心
- **结构清晰**：采用要点式或分条式的回答结构
- **个性化**：基于用户身份提供针对性建议

### 核心要求
1. **身份识别**：首先确认并称呼用户，体现个性化服务
   - 提及用户的昵称或姓氏
   - 了解用户的职位标签（如"管理员"）
   - 体现对用户的关注

2. **专业回答**：
   - 直接、明确地回答问题
   - 提供实用、可操作的建议
   - 避免冗余和无关内容
   - 如需更多信息才能回答，礼貌询问

3. **知识边界**：
   - 对于不确定的问题，诚实说明
   - 建议合适的咨询渠道或专业部门
   - 不编造或臆测信息

4. **企业关怀**：
   - 体现对企业文化和价值观的理解
   - 提供符合企业精神的建议
   - 维护良好的企业形象

### 能力范围
✅ 可以提供：
- 日常工作中的流程咨询
- 企业文化相关问题解答
- 工作方法和效率建议
- 一般性知识问答
- 工作相关的问题分析

❌ 不提供：
- 超出职责范围的决策建议
- 涉及敏感或机密的信息
- 替代专业部门的正式咨询
- 个人财务、医疗等敏感建议

### 表达规范
- 使用敬语和礼貌用语
- 避免过于口语化或俏皮的语言
- 保持积极、专业的服务态度
- 适当使用鼓励性语言

现在请基于以上规范回答用户问题。"""
