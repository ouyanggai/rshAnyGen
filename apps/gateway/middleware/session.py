"""会话管理中间件"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import redis
import uuid
from typing import Callable

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

# 加载配置
config = ConfigLoader()
logger_manager = LogManager("gateway", log_dir=config.get("log_dir", "logs"))
logger = logger_manager.get_logger()


class SessionMiddleware(BaseHTTPMiddleware):
    """会话管理中间件"""

    def __init__(
        self,
        app,
        redis_host: str = None,
        redis_port: int = None,
        redis_db: int = None,
        session_ttl: int = None
    ):
        super().__init__(app)
        # 从配置或参数获取 Redis 配置
        self.redis_host = redis_host or config.get("dependencies.redis.host", "localhost")
        self.redis_port = redis_port or config.get("dependencies.redis.port", 6379)
        self.redis_db = redis_db or config.get("dependencies.redis.db", 0)
        self.session_ttl = session_ttl or config.get("dependencies.redis.ttl", 3600)

        # 创建 Redis 连接
        self._redis_client = None

    @property
    def redis_client(self):
        """延迟创建 Redis 客户端"""
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True
            )
        return self._redis_client

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求，添加会话管理"""

        # 从请求头获取 session_id
        session_id = request.headers.get("X-Session-ID")

        # 如果没有 session_id，生成新的
        if not session_id:
            session_id = f"sess-{uuid.uuid4().hex[:12]}"
            logger.info(f"Created new session: {session_id}")

        # 将 session_id 添加到请求状态
        request.state.session_id = session_id

        # 处理请求
        response = await call_next(request)

        # 将 session_id 返回给客户端
        response.headers["X-Session-ID"] = session_id

        return response

    def close(self):
        """关闭 Redis 连接"""
        if self._redis_client:
            self._redis_client.close()
