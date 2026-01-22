"""Token 计数工具"""
import tiktoken
from typing import List, Dict, Optional
from apps.shared.logger import LogManager

# 创建日志管理器
log_manager = LogManager("token_counter")
logger = log_manager.get_logger()

# 模型对应的编码器
MODEL_ENCODINGS = {
    "qwen-max": "cl100k_base",
    "qwen-plus": "cl100k_base",
    "qwen-turbo": "cl100k_base",
    "gpt-4": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "text-embedding-v3": "cl100k_base",
}


class TokenCounter:
    """Token 计数器"""

    def __init__(self, model: str = "qwen-max"):
        encoding_name = MODEL_ENCODINGS.get(model, "cl100k_base")
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"Failed to get encoding {encoding_name}, using cl100k_base: {e}")
            self.encoding = tiktoken.get_encoding("cl100k_base")
        self.model = model

    def count_text(self, text: str) -> int:
        """计算文本的 token 数"""
        if not text:
            return 0
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Token count error: {e}")
            # 回退到粗略估算: 中文约1.5字符/token, 英文约4字符/token
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            other_chars = len(text) - chinese_chars
            return int(chinese_chars / 1.5 + other_chars / 4)

    def count_message(self, message: Dict) -> int:
        """计算单条消息的 token 数"""
        if not message:
            return 0

        role = message.get("role", "")
        content = message.get("content", "")

        # role + content + overhead (约4 tokens for message formatting)
        role_tokens = self.count_text(role)
        content_tokens = self.count_text(content)

        return role_tokens + content_tokens + 4

    def count_messages(self, messages: List[Dict]) -> int:
        """计算消息列表的总 token 数"""
        if not messages:
            return 0

        total = sum(self.count_message(msg) for msg in messages)
        # 加上回复的预留 tokens (约3 tokens)
        return total + 3

    def trim_messages_to_limit(
        self,
        messages: List[Dict],
        max_tokens: int,
        min_messages: int = 1
    ) -> List[Dict]:
        """裁剪消息列表以符合 token 限制

        Args:
            messages: 消息列表
            max_tokens: 最大 token 数
            min_messages: 最少保留的消息数

        Returns:
            裁剪后的消息列表(保持原始顺序)
        """
        if not messages:
            return []

        if len(messages) <= min_messages:
            return messages.copy()

        # 从最新消息开始累加
        trimmed = []
        current_tokens = 0

        for msg in reversed(messages):
            msg_tokens = self.count_message(msg)

            if current_tokens + msg_tokens > max_tokens:
                if len(trimmed) < min_messages:
                    # 强制包含,保证至少有 min_messages 条
                    trimmed.append(msg)
                    current_tokens += msg_tokens
                else:
                    # 已经达到最小消息数,停止添加
                    break
            else:
                trimmed.append(msg)
                current_tokens += msg_tokens

        # 恢复原始顺序
        return list(reversed(trimmed))

    def estimate_response_tokens(self, prompt_tokens: int, max_response: int = 2000) -> int:
        """估算完整对话的 token 数

        Args:
            prompt_tokens: 提示词 token 数
            max_response: 最大响应 token 数

        Returns:
            估算的总 token 数
        """
        return prompt_tokens + max_response


# 全局实例缓存
_counters: Dict[str, TokenCounter] = {}


def get_token_counter(model: str = "qwen-max") -> TokenCounter:
    """获取 Token 计数器单例"""
    global _counters

    if model not in _counters:
        _counters[model] = TokenCounter(model)

    return _counters[model]


def reset_token_counter_cache():
    """重置计数器缓存"""
    global _counters
    _counters.clear()
