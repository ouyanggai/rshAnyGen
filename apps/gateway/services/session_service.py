import time
import uuid
from typing import Dict, List, Optional

from apps.shared.redis_client import RedisOperations


class SessionService:
    def __init__(self, redis_ops: Optional[RedisOperations] = None):
        self.redis = redis_ops or RedisOperations()

    def _session_key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _user_sessions_key(self, user_id: str) -> str:
        return f"user:sessions:{user_id}"

    def _active_key(self, user_id: str) -> str:
        return f"user:active_session:{user_id}"

    async def create_session(self, user_id: str, title: str = "新会话", session_id: Optional[str] = None) -> Dict:
        await self.redis.init()
        if not session_id:
            session_id = f"sess-{uuid.uuid4().hex[:12]}"
        now = int(time.time())

        session = {
            "session_id": session_id,
            "user_id": user_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }
        await self.redis.hset(self._session_key(session_id), session)
        await self.redis.zadd(self._user_sessions_key(user_id), {session_id: float(now)})
        await self.redis.set_json(self._active_key(user_id), {"session_id": session_id})
        return session

    async def get_session(self, session_id: str) -> Optional[Dict]:
        await self.redis.init()
        data = await self.redis.hgetall(self._session_key(session_id))
        if not data:
            return None
        return {
            "session_id": data.get("session_id", session_id),
            "user_id": data.get("user_id"),
            "title": data.get("title", "新会话"),
            "created_at": int(data.get("created_at") or 0),
            "updated_at": int(data.get("updated_at") or 0),
        }

    async def list_sessions(self, user_id: str, limit: int = 50) -> List[Dict]:
        await self.redis.init()
        session_ids = await self.redis.zrevrange(self._user_sessions_key(user_id), 0, limit - 1)
        sessions: List[Dict] = []
        for sid in session_ids:
            s = await self.get_session(sid)
            if s:
                sessions.append(s)
        return sessions

    async def set_active_session(self, user_id: str, session_id: str) -> None:
        await self.redis.init()
        await self.redis.set_json(self._active_key(user_id), {"session_id": session_id})

    async def get_active_session(self, user_id: str) -> Optional[str]:
        await self.redis.init()
        data = await self.redis.get_json(self._active_key(user_id))
        return data.get("session_id") if data else None

    async def touch_session(self, session_id: str) -> None:
        await self.redis.init()
        data = await self.redis.hgetall(self._session_key(session_id))
        if not data:
            return
        user_id = data.get("user_id")
        if not user_id:
            return
        now = int(time.time())
        await self.redis.hset(self._session_key(session_id), {"updated_at": now})
        await self.redis.zadd(self._user_sessions_key(user_id), {session_id: float(now)})

    async def update_title(self, session_id: str, title: str) -> None:
        await self.redis.init()
        await self.redis.hset(self._session_key(session_id), {"title": title})
        await self.touch_session(session_id)
