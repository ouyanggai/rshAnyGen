"""三级上下文构建器"""
from typing import List, Dict, Optional
from datetime import datetime

from apps.shared.redis_client import RedisOperations
from apps.shared.token_counter import get_token_counter
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("context_builder")
logger = logger_manager.get_logger()

# 配置参数
WORKING_MEMORY_MAX_TOKENS = config.get("context.working_memory.max_tokens", 2048)
WORKING_MEMORY_MIN_TURNS = config.get("context.working_memory.min_turns", 3)
WORKING_MEMORY_MAX_TURNS = config.get("context.working_memory.max_turns", 10)


class ContextBuilder:
    """三级上下文构建器

    构建策略:
    1. 长期记忆 (用户画像) - 从 Redis 获取用户基础信息
    2. 短期摘要 - 从 Redis 获取会话摘要(如果存在)
    3. 工作记忆 - 最近N轮对话,裁剪到符合 token 限制
    4. 当前消息 - 用户最新输入

    Token 预算分配:
    - 长期记忆: ~200 tokens
    - 短期摘要: ~500 tokens
    - 工作记忆: ~2048 tokens
    - 当前消息: ~100 tokens
    """

    def __init__(self, model: str = "qwen-max"):
        self._redis: Optional[RedisOperations] = None
        self.token_counter = get_token_counter(model)
        self.model = model

    @property
    def redis(self) -> RedisOperations:
        """延迟创建 Redis 客户端"""
        if self._redis is None:
            self._redis = RedisOperations()
        return self._redis

    async def build_context(
        self,
        session_id: str,
        user_id: str,
        current_message: str
    ) -> List[Dict]:
        """构建完整上下文

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            current_message: 当前用户消息

        Returns:
            上下文消息列表,可直接用于 LLM 调用
        """
        await self.redis.init()

        context = []
        total_tokens = 0

        # === 第一层: 长期记忆 (用户画像) ===
        user_memory = await self._build_user_memory(user_id)
        if user_memory:
            context.append(user_memory)
            total_tokens += self.token_counter.count_message(user_memory)
            logger.debug(f"User memory added: {self.token_counter.count_message(user_memory)} tokens")

        # === 第二层: 短期摘要 ===
        summary = await self._get_session_summary(session_id)
        if summary:
            summary_msg = {
                "role": "system",
                "content": f"【对话摘要】\n{summary}"
            }
            context.append(summary_msg)
            total_tokens += self.token_counter.count_message(summary_msg)
            logger.debug(f"Summary added: {self.token_counter.count_message(summary_msg)} tokens")

        # === 第三层: 工作记忆 ===
        working_memory = await self._build_working_memory(session_id)
        if working_memory:
            context.extend(working_memory)
            working_tokens = sum(
                self.token_counter.count_message(msg) for msg in working_memory
            )
            total_tokens += working_tokens
            logger.debug(f"Working memory added: {len(working_memory)} messages, {working_tokens} tokens")

        # === 第四层: 当前消息 ===
        current_msg = {"role": "user", "content": current_message}
        context.append(current_msg)
        total_tokens += self.token_counter.count_message(current_msg)

        logger.info(
            f"Context built: {len(context)} messages, {total_tokens} total tokens "
            f"(user_memory: {bool(user_memory)}, summary: {bool(summary)}, "
            f"working_memory: {len(working_memory)} messages)"
        )

        return context

    async def _build_user_memory(self, user_id: str) -> Optional[Dict]:
        """构建用户画像记忆"""
        user_info = await self.redis.hgetall(f"user:{user_id}")
        if not user_info:
            return None

        # 构建用户信息内容
        content_parts = ["【用户信息】"]

        # 昵称
        nickname = user_info.get("nickname", "")
        if nickname:
            content_parts.append(f"昵称: {nickname}")

        # 用户标签
        tags = await self.redis.smembers(f"user:tags:{user_id}")
        if tags:
            content_parts.append(f"标签: {', '.join(tags)}")

        # 实体信息 (最近提及的人/项目等)
        entities = await self._get_user_entities(user_id, limit=5)
        if entities:
            entity_summaries = []
            for entity in entities[:5]:
                entity_type = entity.get("type", "")
                entity_name = entity.get("name", "")
                if entity_type and entity_name:
                    entity_summaries.append(f"{entity_name}({entity_type})")
            if entity_summaries:
                content_parts.append(f"相关实体: {', '.join(entity_summaries)}")

        if len(content_parts) == 1:
            return None

        return {
            "role": "system",
            "content": "\n".join(content_parts)
        }

    async def _get_user_entities(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """获取用户相关的实体"""
        entities = []

        # 从各类型的实体集合中获取
        for entity_type in ["person", "project", "location", "concept"]:
            entity_ids = await self.redis.zrevrange(
                f"user:entities:{entity_type}:{user_id}",
                0,
                limit - 1
            )

            for entity_id in entity_ids:
                data = await self.redis.hgetall(f"entity:{entity_id}")
                if data:
                    data["entity_id"] = entity_id
                    entities.append(data)

        # 按提及次数排序
        entities.sort(
            key=lambda e: int(e.get("mention_count", 0)),
            reverse=True
        )

        return entities[:limit]

    async def _get_session_summary(self, session_id: str) -> Optional[str]:
        """获取会话摘要"""
        summaries = await self.redis.lrange_json(
            f"session:summaries:{session_id}",
            0,
            -1
        )

        if not summaries:
            return None

        # 合并所有摘要段
        summary_parts = []
        for item in summaries:
            topic = item.get("topic", "")
            summary = item.get("summary", "")
            if topic and summary:
                summary_parts.append(f"[{topic}] {summary}")

        return "\n".join(summary_parts) if summary_parts else None

    async def _build_working_memory(self, session_id: str) -> List[Dict]:
        """构建工作记忆"""
        all_messages = await self.redis.lrange_json(
            f"session:messages:{session_id}",
            0,
            -1
        )

        if not all_messages:
            return []

        # 先限制最大轮数
        if len(all_messages) > WORKING_MEMORY_MAX_TURNS * 2:
            all_messages = all_messages[-WORKING_MEMORY_MAX_TURNS * 2:]

        # 使用 token counter 裁剪到符合限制
        working_memory = self.token_counter.trim_messages_to_limit(
            all_messages,
            max_tokens=WORKING_MEMORY_MAX_TOKENS,
            min_messages=WORKING_MEMORY_MIN_TURNS * 2
        )

        return working_memory

    async def estimate_context_tokens(
        self,
        session_id: str,
        user_id: str,
        current_message: str
    ) -> int:
        """估算构建的上下文 token 数(不实际构建)"""
        tokens = 0

        # 当前消息
        tokens += self.token_counter.count_text(current_message)

        # 用户信息 (估算)
        tokens += 200

        # 摘要 (如果有)
        # 需要实际查询才能准确计算,这里给个估算值
        tokens += 500

        # 工作记忆
        await self.redis.init()
        messages = await self.redis.lrange_json(
            f"session:messages:{session_id}",
            -WORKING_MEMORY_MIN_TURNS * 2,
            -1
        )
        if messages:
            tokens += sum(
                self.token_counter.count_message(msg) for msg in messages
            )

        return tokens


# 全局实例缓存
_context_builders: Dict[str, ContextBuilder] = {}


def get_context_builder(model: str = "qwen-max") -> ContextBuilder:
    """获取上下文构建器单例"""
    global _context_builders

    if model not in _context_builders:
        _context_builders[model] = ContextBuilder(model)

    return _context_builders[model]
