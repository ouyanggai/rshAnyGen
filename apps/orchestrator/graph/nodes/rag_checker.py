"""RAG Checker Node - 快速检查知识库是否有相关内容"""
from typing import Dict, Any
from ..state import AgentState
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("orchestrator")
logger = logger_manager.get_logger()


async def rag_checker(state: AgentState) -> AgentState:
    """快速检查知识库是否有相关内容

    检查是否有相关内容：
    - 搜索 top_k=10 个结果
    - 如果有任何结果包含用户查询的关键词，认为相关
    - 或者如果有足够高的相似度分数

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态
    """
    query = state.get("user_message")

    if not query:
        state["rag_has_relevant"] = False
        return state

    try:
        from apps.orchestrator.services.rag_pipeline import RAGPipelineClient

        client = RAGPipelineClient()
        try:
            # 搜索更多结果，避免漏掉相关内容
            results = await client.search(query, top_k=10)

            # 检查是否有相关结果
            has_relevant = False
            best_score = 0
            best_match_content = ""

            if results and len(results) > 0:
                for result in results:
                    score = result.get("score", 0)
                    content = result.get("content", "")

                    # 更新最佳分数
                    if score > best_score:
                        best_score = score
                        best_match_content = content[:100]

                    # 检查是否有相关性
                    # 1. 如果包含用户查询中的关键词
                    # 2. 或者相似度分数足够高
                    if score > 0.02 or (score > 0.015 and _contains_keywords(query, content)):
                        has_relevant = True
                        break

                if has_relevant:
                    logger.info(f"RAG check found relevant content (score: {best_score:.4f}): {best_match_content}...")
                else:
                    logger.info(f"RAG check found no relevant content (best score: {best_score:.4f})")
            else:
                logger.info("RAG check found no results")

            state["rag_has_relevant"] = has_relevant

        finally:
            await client.close()

    except Exception as e:
        logger.error(f"Error in RAG checker: {e}")
        # 出错时假设没有相关内容，走正常流程
        state["rag_has_relevant"] = False

    return state


def _contains_keywords(query: str, content: str) -> bool:
    """检查内容是否包含查询中的关键词

    提取查询中的关键词（通常是2个字以上的词），检查是否在内容中

    Args:
        query: 用户查询
        content: 文档内容

    Returns:
        是否包含关键词
    """
    import re

    # 提取查询中的中文关键词（2个字以上）
    keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', query)

    if not keywords:
        return False

    content_lower = content.lower()
    for keyword in keywords:
        if keyword.lower() in content_lower:
            return True

    return False
