"""内部知识库查询 Skill API"""
from typing import Dict, Any, List


def invoke(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """执行知识库查询

    Args:
        args: 查询参数
            - query (str): 查询内容
            - top_k (int): 返回结果数量
        context: 执行上下文

    Returns:
        查询结果
    """
    query = args.get("query", "")
    top_k = args.get("top_k", 5)

    # 参数验证
    if not query:
        raise ValueError("query 参数不能为空")

    if top_k < 1 or top_k > 10:
        top_k = min(max(top_k, 1), 10)

    # TODO: 连接实际的 RAG Pipeline
    # 这里返回模拟数据
    # 实际实现应该：
    # 1. 连接向量数据库
    # 2. 执行相似度检索
    # 3. 返回最相关的文档

    mock_results = [
        {
            "doc_id": f"doc-{i}",
            "title": f"相关文档 {i}",
            "content": f"这是关于 '{query}' 的文档内容片段 {i}...",
            "score": 0.95 - (i * 0.05),
            "metadata": {
                "source": "internal_kb",
                "last_updated": "2024-01-01"
            }
        }
        for i in range(min(top_k, 3))
    ]

    return {
        "results": mock_results,
        "total": len(mock_results),
        "query": query
    }
