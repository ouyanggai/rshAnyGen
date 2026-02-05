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
    kb_ids = context.get("kb_ids") or args.get("kb_ids") or None

    # 参数验证
    if not query:
        raise ValueError("query 参数不能为空")

    if top_k < 1 or top_k > 10:
        top_k = min(max(top_k, 1), 10)

    # 调用 RAG Pipeline
    try:
        import httpx
        from apps.shared.config_loader import ConfigLoader

        config = ConfigLoader().load_defaults()
        port = config.get("ports", {}).get("rag_pipeline", 9305)
        base_url = f"http://localhost:{port}"

        payload = {"query": query, "top_k": top_k, "rerank": True, "kb_ids": kb_ids}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{base_url}/api/v1/search", json=payload)
            resp.raise_for_status()
            raw_results = resp.json() or []

        results = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            chunk_id = item.get("chunk_id")
            content = item.get("content")
            results.append(
                {
                    "doc_id": chunk_id,
                    "title": metadata.get("title") or metadata.get("source") or chunk_id,
                    "content": content,
                    "score": item.get("score", 0),
                    "metadata": metadata,
                }
            )

        return {
            "results": results,
            "total": len(results),
            "query": query,
            "kb_ids": kb_ids or [],
        }

    except Exception as e:
        # 不中断主流程：返回可解释的错误信息给上层 LLM
        return {
            "results": [],
            "total": 0,
            "query": query,
            "kb_ids": kb_ids or [],
            "error": str(e),
        }
