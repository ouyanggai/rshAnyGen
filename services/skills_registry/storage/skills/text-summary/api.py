"""文本摘要 Skill API"""
from typing import Dict, Any


def invoke(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """执行文本摘要

    Args:
        args: 摘要参数
            - text (str): 待摘要的文本
            - max_length (int): 摘要最大长度
            - style (str): 摘要风格
        context: 执行上下文

    Returns:
        摘要结果
    """
    text = args.get("text", "")
    max_length = args.get("max_length", 200)
    style = args.get("style", "concise")

    # 参数验证
    if not text:
        raise ValueError("text 参数不能为空")

    if max_length < 50 or max_length > 1000:
        max_length = min(max(max_length, 50), 1000)

    if style not in ["concise", "bullet", "detailed"]:
        style = "concise"

    # TODO: 调用实际的 LLM 进行摘要
    # 实现方案：
    # 1. 构建摘要提示词
    # 2. 调用 LLM API
    # 3. 解析并返回摘要结果

    # 简单截断作为示例
    if len(text) <= max_length:
        summary = text
    else:
        summary = text[:max_length] + "..."

    return {
        "summary": summary,
        "original_length": len(text),
        "summary_length": len(summary),
        "compression_ratio": round(len(summary) / len(text), 3),
        "style": style
    }
