"""Redis 操作封装 - 支持 JSON 和列表操作"""
import redis
import json
from typing import List, Optional, Any, Dict
from datetime import datetime

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
log_manager = LogManager("redis_client")
logger = log_manager.get_logger()


class InMemoryRedis:
    def __init__(self):
        self._kv: Dict[str, Any] = {}
        self._lists: Dict[str, List[Any]] = {}
        self._hashes: Dict[str, Dict[str, Any]] = {}
        self._sets: Dict[str, set] = {}
        self._zsets: Dict[str, Dict[str, float]] = {}

    def ping(self):
        return True

    def get(self, key: str):
        return self._kv.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None):
        self._kv[key] = value
        return True

    def setex(self, key: str, ttl: int, value: Any):
        self._kv[key] = value
        return True

    def delete(self, key: str):
        self._kv.pop(key, None)
        self._lists.pop(key, None)
        self._hashes.pop(key, None)
        self._sets.pop(key, None)
        self._zsets.pop(key, None)
        return 1

    def ttl(self, key: str):
        return -1

    def keys(self, pattern: str):
        import fnmatch

        all_keys = set(self._kv.keys()) | set(self._lists.keys()) | set(self._hashes.keys()) | set(self._sets.keys()) | set(self._zsets.keys())
        return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]

    def rpush(self, key: str, value: Any):
        self._lists.setdefault(key, []).append(value)
        return len(self._lists[key])

    def llen(self, key: str):
        return len(self._lists.get(key, []))

    def lrange(self, key: str, start: int, end: int):
        items = self._lists.get(key, [])
        if end == -1:
            end = len(items) - 1
        return items[start : end + 1]

    def lpop(self, key: str):
        items = self._lists.get(key, [])
        if not items:
            return None
        value = items.pop(0)
        if not items:
            self._lists.pop(key, None)
        return value

    def ltrim(self, key: str, start: int, end: int):
        items = self._lists.get(key, [])
        if end == -1:
            end = len(items) - 1
        self._lists[key] = items[start : end + 1]
        return True

    def hset(self, key: str, mapping: Dict[str, Any]):
        self._hashes.setdefault(key, {}).update({k: str(v) for k, v in mapping.items()})
        return True

    def hgetall(self, key: str):
        return self._hashes.get(key, {})

    def sadd(self, key: str, *values: Any):
        s = self._sets.setdefault(key, set())
        for v in values:
            s.add(str(v))
        return len(values)

    def smembers(self, key: str):
        return self._sets.get(key, set())

    def srem(self, key: str, *values: Any):
        s = self._sets.get(key, set())
        removed = 0
        for v in values:
            if str(v) in s:
                s.remove(str(v))
                removed += 1
        return removed

    def zadd(self, key: str, mapping: Dict[str, float]):
        z = self._zsets.setdefault(key, {})
        for member, score in mapping.items():
            z[str(member)] = float(score)
        return True

    def zrevrange(self, key: str, start: int, end: int):
        z = self._zsets.get(key, {})
        items = sorted(z.items(), key=lambda kv: kv[1], reverse=True)
        if end == -1:
            end = len(items) - 1
        return [m for m, _s in items[start : end + 1]]

    def zrange(self, key: str, start: int, end: int):
        z = self._zsets.get(key, {})
        items = sorted(z.items(), key=lambda kv: kv[1])
        if end == -1:
            end = len(items) - 1
        return [m for m, _s in items[start : end + 1]]


_INMEMORY_REDIS = InMemoryRedis()


class RedisOperations:
    """Redis 操作封装类

    提供常用操作的封装,包括:
    - JSON 列表操作 (存储消息等结构化数据)
    - Hash 操作 (存储用户信息等)
    - Set 操作 (存储标签等)
    """

    def __init__(self, redis_client: redis.Redis = None):
        self._redis_client = redis_client
        self._initialized = False

    async def init(self):
        """初始化 Redis 连接"""
        if not self._initialized:
            self._initialized = True
            # 触发连接
            _ = self.client

    @property
    def client(self) -> redis.Redis:
        """获取 Redis 客户端(延迟创建)"""
        if self._redis_client is None:
            host = config.get("dependencies.redis.host", "192.168.1.248")
            port = config.get("dependencies.redis.port", 6379)
            db = config.get("dependencies.redis.db", 0)
            client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            try:
                client.ping()
                self._redis_client = client
            except Exception as e:
                logger.warning(f"Redis unavailable ({host}:{port}/{db}), fallback to in-memory: {e}")
                self._redis_client = _INMEMORY_REDIS
        return self._redis_client

    # === JSON 列表操作 ===

    async def rpush_json(self, key: str, data: Dict) -> int:
        """将 JSON 数据推入列表右端"""
        json_str = json.dumps(data, ensure_ascii=False)
        return self.client.rpush(key, json_str)

    async def lrange_json(
        self,
        key: str,
        start: int,
        end: int
    ) -> List[Dict]:
        """获取列表范围内的 JSON 数据"""
        values = self.client.lrange(key, start, end)
        if not values:
            return []
        return [json.loads(v) for v in values]

    async def lpop_json(self, key: str) -> Optional[Dict]:
        """从列表左端弹出 JSON 数据"""
        value = self.client.lpop(key)
        if value is None:
            return None
        return json.loads(value)

    async def llen(self, key: str) -> int:
        """获取列表长度"""
        return self.client.llen(key)

    async def trim_list(self, key: str, start: int, end: int):
        """裁剪列表"""
        self.client.ltrim(key, start, end)

    # === Hash 操作 ===

    async def hset_json(self, key: str, field: str, data: Dict):
        """存储 JSON 数据到 Hash"""
        json_str = json.dumps(data, ensure_ascii=False)
        self.client.hset(key, field, json_str)

    async def hget_json(self, key: str, field: str) -> Optional[Dict]:
        """从 Hash 获取 JSON 数据"""
        value = self.client.hget(key, field)
        if value is None:
            return None
        return json.loads(value)

    async def hgetall(self, key: str) -> Dict[str, str]:
        """获取 Hash 所有字段"""
        return self.client.hgetall(key)

    async def hset(self, key: str, mapping: Dict[str, Any]):
        """设置 Hash 多个字段"""
        # 将值转换为字符串
        str_mapping = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                      for k, v in mapping.items()}
        self.client.hset(key, mapping=str_mapping)

    async def hincrby(self, key: str, field: str, amount: int = 1):
        """Hash 字段自增"""
        return self.client.hincrby(key, field, amount)

    async def hdel(self, key: str, *fields: str):
        """删除 Hash 字段"""
        if fields:
            self.client.hdel(key, *fields)

    # === Set 操作 ===

    async def sadd(self, key: str, *values: Any):
        """向集合添加元素"""
        str_values = [str(v) for v in values]
        self.client.sadd(key, *str_values)

    async def srem(self, key: str, *values: Any):
        """从集合删除元素"""
        str_values = [str(v) for v in values]
        self.client.srem(key, *str_values)

    async def smembers(self, key: str) -> set:
        """获取集合所有元素"""
        return self.client.smembers(key)

    async def scard(self, key: str) -> int:
        """获取集合元素数量"""
        return self.client.scard(key)

    # === Sorted Set 操作 ===

    async def zadd(self, key: str, mapping: Dict[str, float]):
        """向有序集合添加元素"""
        self.client.zadd(key, mapping)

    async def zrange(
        self,
        key: str,
        start: int = 0,
        end: int = -1,
        desc: bool = False
    ) -> List[str]:
        """获取有序集合范围内的元素"""
        return self.client.zrange(key, start, end, desc=desc)

    async def zrevrange(self, key: str, start: int, end: int) -> List[str]:
        """获取有序集合范围内元素(降序)"""
        return self.client.zrevrange(key, start, end)

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float):
        """按分数范围删除有序集合元素"""
        self.client.zremrangebyscore(key, min_score, max_score)

    # === 通用操作 ===

    async def delete(self, *keys: str):
        """删除键"""
        if keys:
            self.client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self.client.exists(key) > 0

    async def expire(self, key: str, seconds: int):
        """设置键过期时间"""
        self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """获取键的剩余过期时间"""
        return self.client.ttl(key)

    async def keys(self, pattern: str) -> List[str]:
        """查找匹配的键"""
        return self.client.keys(pattern)

    async def get_json(self, key: str) -> Optional[Dict]:
        """获取 JSON 数据"""
        value = self.client.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def set_json(
        self,
        key: str,
        data: Dict,
        ex: Optional[int] = None
    ):
        """设置 JSON 数据"""
        json_str = json.dumps(data, ensure_ascii=False)
        self.client.set(key, json_str, ex=ex)

    # === 连接管理 ===

    def close(self):
        """关闭连接"""
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None
            self._initialized = False

    def ping(self) -> bool:
        """测试连接"""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping error: {e}")
            return False


# 全局实例
_redis_instance: Optional[RedisOperations] = None


def get_redis() -> RedisOperations:
    """获取 Redis 操作单例"""
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = RedisOperations()
    return _redis_instance
