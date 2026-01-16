"""通用对话 Skill API"""
from typing import Dict, Any


def invoke(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """执行通用对话

    Args:
        args: 对话参数
            - message (str): 对话内容
        context: 执行上下文

    Returns:
        对话回复
    """
    message = args.get("message", "")

    # 参数验证
    if not message:
        raise ValueError("message 参数不能为空")

    # TODO: 调用实际的 LLM 生成回复
    # 实际实现应该：
    # 1. 连接 LLM API (如 OpenAI, Anthropic, 或本地模型)
    # 2. 发送对话历史和当前消息
    # 3. 返回生成的回复

    # 暂时回显消息作为示例
    return {
        "reply": f"收到消息: {message}",
        "model": "mock-llm",
        "tokens_used": len(message.split())
    }
