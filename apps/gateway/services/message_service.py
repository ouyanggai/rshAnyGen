import time
from typing import Dict, List, Optional

from apps.shared.redis_client import RedisOperations


class MessageService:
    def __init__(self, redis_ops: Optional[RedisOperations] = None):
        self.redis = redis_ops or RedisOperations()

    def _messages_key(self, session_id: str) -> str:
        return f"session:messages:{session_id}"

    async def append_message(self, session_id: str, role: str, content: str) -> Dict:
        await self.redis.init()
        item = {"role": role, "content": content, "ts": int(time.time())}
        await self.redis.rpush_json(self._messages_key(session_id), item)
        return item

    async def list_messages(self, session_id: str, limit: int = 50) -> List[Dict]:
        await self.redis.init()
        if limit <= 0:
            return []
        total = await self.redis.llen(self._messages_key(session_id))
        start = max(0, total - limit)
        return await self.redis.lrange_json(self._messages_key(session_id), start, -1)

