# 多轮对话与长期记忆系统实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现类似 Claude Web 版的多轮对话、历史会话管理和长期记忆功能

**Architecture:** 使用 Redis 存储会话历史和用户信息，Milvus 存储语义记忆向量，混合模式（近期消息+历史摘要）管理上下文

**Tech Stack:** Redis (aioredis), Milvus (pymilvus), FastAPI, React

---

## Phase 1: Redis 配置与基础服务

### Task 1: 更新 Redis 配置

**Files:**
- Modify: `config/default.yaml`

**Step 1: 添加 Redis 上下文和记忆配置**

```yaml
# 在 dependencies.redis 下添加
dependencies:
  redis:
    host: "192.168.1.248"
    port: 6379
    db: 0
    ttl: 3600
    # 新增：上下文配置
    context:
      window_size: 10           # 近期完整消息数量
      summary_threshold: 20     # 触发摘要的消息阈值
      summary_interval: 10      # 每N条消息检查一次
    # 新增：记忆配置
    memory:
      collection_name: "user_memories"
      embedding_model: "text-embedding-v3"
      retrieval_top_k: 3
      importance_threshold: 0.5
```

**Step 2: 添加 Admin 配置**

```yaml
# 在文件末尾添加
admin:
  secret_phrase: "admin_secret_key"  # 暗语
  fixed_user_id: "admin-001"
```

**Step 3: 验证配置加载**

Run: `python -c "from apps.shared.config_loader import ConfigLoader; c = ConfigLoader(); print(c.get('dependencies.redis.context'))"`

Expected: `{'window_size': 10, 'summary_threshold': 20, 'summary_interval': 10}`

**Step 4: Commit**

```bash
git add config/default.yaml
git commit -m "config: add redis context and memory configuration"
```

---

### Task 2: 创建 Redis 客户端服务

**Files:**
- Create: `apps/shared/redis_client.py`
- Modify: `apps/gateway/requirements.txt`
- Modify: `apps/orchestrator/requirements.txt`

**Step 1: 添加 aioredis 依赖**

```bash
# apps/gateway/requirements.txt 和 apps/orchestrator/requirements.txt 都添加
echo "aioredis==2.0.1" >> apps/gateway/requirements.txt
echo "aioredis==2.0.1" >> apps/orchestrator/requirements.txt
```

**Step 2: 安装依赖**

Run: `pip install -r apps/gateway/requirements.txt`

Expected: 安装成功无报错

**Step 3: 创建 Redis 客户端**

```python
# apps/shared/redis_client.py
"""Redis 客户端服务"""
import json
from typing import Optional, Any, List
from aioredis import Redis, from_url
from contextlib import asynccontextmanager

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("redis")
logger = logger_manager.get_logger()


class RedisClient:
    """Redis 客户端单例"""

    _instance: Optional[Redis] = None

    @classmethod
    async def get_client(cls) -> Redis:
        """获取 Redis 客户端实例"""
        if cls._instance is None:
            redis_config = config.get("dependencies.redis")
            redis_url = f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config['db']}"

            cls._instance = await from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"Connected to Redis at {redis_config['host']}:{redis_config['port']}")

        return cls._instance

    @classmethod
    async def close(cls):
        """关闭连接"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None


class RedisOperations:
    """Redis 操作封装"""

    def __init__(self):
        self.client: Optional[Redis] = None

    async def init(self):
        """初始化"""
        self.client = await RedisClient.get_client()

    async def hget_json(self, key: str, field: str = None) -> Any:
        """获取 Hash 字段的 JSON 值"""
        value = await self.client.hget(key, field) if field else await self.client.hgetall(key)
        return json.loads(value) if isinstance(value, str) else value

    async def hset_json(self, key: str, field: str, value: Any):
        """设置 Hash 字段的 JSON 值"""
        await self.client.hset(key, field, json.dumps(value))

    async def lpush_json(self, key: str, value: Any):
        """从左侧推入 JSON 值到 List"""
        await self.client.lpush(key, json.dumps(value))

    async def rpush_json(self, key: str, value: Any):
        """从右侧推入 JSON 值到 List"""
        await self.client.rpush(key, json.dumps(value))

    async def lrange_json(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取 List 范围内的 JSON 值"""
        values = await self.client.lrange(key, start, end)
        return [json.loads(v) for v in values]

    async def zadd_with_score(self, key: str, mapping: dict):
        """添加到 Sorted Set"""
        await self.client.zadd(key, mapping)

    async def zrevrange_json(self, key: str, start: int = 0, end: int = -1) -> List[tuple]:
        """按分数倒序获取 Sorted Set"""
        return await self.client.zrevrange(key, start, end, withscores=True)
```

**Step 4: 创建测试文件**

```python
# tests/shared/test_redis_client.py
import pytest
from apps.shared.redis_client import RedisClient, RedisOperations


@pytest.mark.asyncio
async def test_redis_connection():
    """测试 Redis 连接"""
    client = await RedisClient.get_client()
    assert client is not None
    await RedisClient.close()


@pytest.mark.asyncio
async def test_redis_operations():
    """测试 Redis 操作"""
    ops = RedisOperations()
    await ops.init()

    # 测试 hset/hget
    await ops.hset_json("test:hash", "field1", {"key": "value"})
    result = await ops.hget_json("test:hash", "field1")
    assert result == {"key": "value"}

    # 测试 lpush/lrange
    await ops.rpush_json("test:list", {"msg": "hello"})
    results = await ops.lrange_json("test:list", 0, -1)
    assert len(results) == 1
    assert results[0] == {"msg": "hello"}

    # 清理
    await ops.client.delete("test:hash", "test:list")
```

**Step 5: 运行测试**

Run: `pytest tests/shared/test_redis_client.py -v`

Expected: PASS

**Step 6: Commit**

```bash
git add apps/shared/redis_client.py apps/gateway/requirements.txt apps/orchestrator/requirements.txt tests/shared/test_redis_client.py
git commit -m "feat: add redis client service with async operations"
```

---

## Phase 2: 用户认证系统

### Task 3: 创建用户模型和服务

**Files:**
- Create: `apps/gateway/models/auth.py`
- Create: `apps/gateway/services/user_service.py`

**Step 1: 定义用户模型**

```python
# apps/gateway/models/auth.py
"""用户认证相关模型"""
from pydantic import BaseModel, Field
from typing import Optional, Dict


class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    nickname: str = Field(..., min_length=1, max_length=20, description="用户昵称")


class UserPreferences(BaseModel):
    """用户偏好设置"""
    default_model: str = "qwen-max"
    temperature: float = 0.7
    default_search: bool = False


class UserInfo(BaseModel):
    """用户信息"""
    user_id: str
    nickname: str
    ip_address: str
    created_at: str
    last_seen: str
    preferences: UserPreferences


class UserRegisterResponse(BaseModel):
    """用户注册响应"""
    user_id: str
    nickname: str
    is_new: bool
    preferences: Optional[UserPreferences] = None
```

**Step 2: 创建用户服务**

```python
# apps/gateway/services/user_service.py
"""用户管理服务"""
import uuid
from datetime import datetime
from typing import Optional

from apps.gateway.models.auth import UserRegisterRequest, UserInfo, UserPreferences, UserRegisterResponse
from apps.shared.redis_client import RedisOperations
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("user_service")
logger = logger_manager.get_logger()


class UserService:
    """用户服务"""

    ADMIN_USER_ID = config.get("admin.fixed_user_id", "admin-001")
    ADMIN_SECRET = config.get("admin.secret_phrase", "admin_secret_key")

    def __init__(self):
        self.redis = RedisOperations()

    async def register_or_login(self, nickname: str, ip_address: str) -> UserRegisterResponse:
        """注册或登录用户

        Args:
            nickname: 用户昵称 或 admin 暗语
            ip_address: 客户端 IP 地址

        Returns:
            UserRegisterResponse
        """
        await self.redis.init()

        # 检查是否是 admin 暗语
        if nickname == self.ADMIN_SECRET:
            return await self._get_admin_user()

        # 检查 IP 是否已注册
        existing_user_id = await self.redis.client.get(f"ip:user:{ip_address}")

        if existing_user_id:
            # 已存在用户，更新昵称
            user_info = await self.redis.hgetall(f"user:{existing_user_id}")
            user_info["nickname"] = nickname
            user_info["last_seen"] = datetime.now().isoformat()
            await self.redis.client.hset(f"user:{existing_user_id}", mapping=user_info)

            logger.info(f"User updated: {existing_user_id}, nickname: {nickname}")
            return UserRegisterResponse(
                user_id=existing_user_id,
                nickname=nickname,
                is_new=False,
                preferences=UserPreferences(**user_info.get("preferences", {}))
            )

        # 创建新用户
        user_id = f"user-{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        user_data = {
            "user_id": user_id,
            "nickname": nickname,
            "ip_address": ip_address,
            "created_at": now,
            "last_seen": now,
            "preferences": UserPreferences().dict()
        }

        # 保存用户信息
        await self.redis.client.hset(f"user:{user_id}", mapping=user_data)
        await self.redis.client.set(f"ip:user:{ip_address}", user_id)

        logger.info(f"New user created: {user_id}, nickname: {nickname}")
        return UserRegisterResponse(
            user_id=user_id,
            nickname=nickname,
            is_new=True,
            preferences=UserPreferences()
        )

    async def _get_admin_user(self) -> UserRegisterResponse:
        """获取 admin 用户"""
        await self.redis.init()

        user_data = {
            "user_id": self.ADMIN_USER_ID,
            "nickname": "Admin",
            "ip_address": "localhost",
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "preferences": {
                "default_model": "qwen-max",
                "temperature": 0.7,
                "default_search": False
            }
        }

        # 确保 admin 用户存在
        existing = await self.redis.client.hgetall(f"user:{self.ADMIN_USER_ID}")
        if not existing:
            await self.redis.client.hset(f"user:{self.ADMIN_USER_ID}", mapping=user_data)

        return UserRegisterResponse(
            user_id=self.ADMIN_USER_ID,
            nickname="Admin",
            is_new=False,
            preferences=UserPreferences(**user_data["preferences"])
        )

    async def get_user(self, user_id: str) -> Optional[UserInfo]:
        """获取用户信息"""
        await self.redis.init()
        user_data = await self.redis.client.hgetall(f"user:{user_id}")

        if not user_data:
            return None

        return UserInfo(
            user_id=user_data["user_id"],
            nickname=user_data["nickname"],
            ip_address=user_data["ip_address"],
            created_at=user_data["created_at"],
            last_seen=user_data["last_seen"],
            preferences=UserPreferences(**user_data.get("preferences", {}))
        )

    async def update_preferences(self, user_id: str, preferences: dict) -> bool:
        """更新用户偏好"""
        await self.redis.init()
        await self.redis.hset_json(f"user:{user_id}", "preferences", preferences)
        return True
```

**Step 3: 创建测试**

```python
# tests/gateway/services/test_user_service.py
import pytest
from apps.gateway.services.user_service import UserService


@pytest.mark.asyncio
async def test_register_new_user():
    """测试注册新用户"""
    service = UserService()
    response = await service.register_or_login("测试用户", "192.168.1.100")

    assert response.is_new is True
    assert response.nickname == "测试用户"
    assert response.user_id.startswith("user-")


@pytest.mark.asyncio
async def test_existing_user_update_nickname():
    """测试已存在用户更新昵称"""
    service = UserService()

    # 首次注册
    response1 = await service.register_or_login("原始昵称", "192.168.1.101")
    assert response1.is_new is True

    # 相同 IP，更新昵称
    response2 = await service.register_or_login("新昵称", "192.168.1.101")
    assert response2.is_new is False
    assert response2.nickname == "新昵称"
    assert response2.user_id == response1.user_id


@pytest.mark.asyncio
async def test_admin_login():
    """测试 admin 暗语登录"""
    service = UserService()
    response = await service.register_or_login("admin_secret_key", "localhost")

    assert response.user_id == "admin-001"
    assert response.nickname == "Admin"
```

**Step 4: 运行测试**

Run: `pytest tests/gateway/services/test_user_service.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/gateway/models/auth.py apps/gateway/services/user_service.py tests/gateway/services/test_user_service.py
git commit -m "feat: add user authentication service with nickname registration"
```

---

### Task 4: 创建用户认证路由

**Files:**
- Create: `apps/gateway/routers/auth.py`
- Modify: `apps/gateway/main.py`

**Step 1: 创建认证路由**

```python
# apps/gateway/routers/auth.py
"""用户认证路由"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from apps.gateway.models.auth import UserRegisterRequest, UserRegisterResponse
from apps.gateway.services.user_service import UserService
from apps.shared.logger import LogManager

logger_manager = LogManager("auth")
logger = logger_manager.get_logger()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserRegisterResponse)
async def register(request: UserRegisterRequest, req: Request):
    """注册或登录用户

    根据客户端 IP 和昵称进行注册：
    - 首次访问：创建新用户
    - 已存在 IP：更新昵称
    - Admin 暗语：返回管理员权限
    """
    # 获取客户端 IP
    forwarded = req.headers.get("X-Forwarded-For")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        ip_address = req.client.host

    logger.info(f"Register request: nickname={request.nickname}, ip={ip_address}")

    try:
        service = UserService()
        response = await service.register_or_login(request.nickname, ip_address)
        return response
    except Exception as e:
        logger.error(f"Register error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_me(req: Request):
    """获取当前用户信息

    从请求头 X-User-Id 获取用户信息
    """
    user_id = req.headers.get("X-User-Id")

    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not provided")

    service = UserService()
    user_info = await service.get_user(user_id)

    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")

    return user_info


@router.put("/preferences")
async def update_preferences(preferences: dict, req: Request):
    """更新用户偏好设置"""
    user_id = req.headers.get("X-User-Id")

    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not provided")

    service = UserService()
    success = await service.update_preferences(user_id, preferences)

    return {"success": success}
```

**Step 2: 注册路由到主应用**

```python
# apps/gateway/main.py
# 在现有路由注册后添加
from apps.gateway.routers import auth

# 注册 auth 路由
app.include_router(auth.router, tags=["Auth"])
```

**Step 3: 测试 API**

Run: `curl -X POST http://localhost:9301/api/v1/auth/register -H "Content-Type: application/json" -d '{"nickname": "测试用户"}'`

Expected: 返回包含 user_id, nickname, is_new 的 JSON

**Step 4: Commit**

```bash
git add apps/gateway/routers/auth.py apps/gateway/main.py
git commit -m "feat: add user authentication routes"
```

---

## Phase 3: 会话管理系统

### Task 5: 创建会话模型和服务

**Files:**
- Create: `apps/gateway/models/session.py`
- Create: `apps/gateway/services/session_service.py`

**Step 1: 定义会话模型**

```python
# apps/gateway/models/session.py
"""会话相关模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SessionMessage(BaseModel):
    """会话消息"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    timestamp: str


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    user_id: str
    title: Optional[str] = None


class UpdateSessionTitleRequest(BaseModel):
    """更新会话标题请求"""
    title: str


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    model: str
    kb_ids: List[str]


class SessionDetail(BaseModel):
    """会话详情（包含消息）"""
    session: SessionInfo
    messages: List[SessionMessage]
```

**Step 2: 创建会话服务**

```python
# apps/gateway/services/session_service.py
"""会话管理服务"""
import uuid
from datetime import datetime
from typing import List, Optional

from apps.gateway.models.session import (
    CreateSessionRequest, SessionInfo, SessionDetail,
    SessionMessage, UpdateSessionTitleRequest
)
from apps.shared.redis_client import RedisOperations
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("session_service")
logger = logger_manager.get_logger()


class SessionService:
    """会话服务"""

    def __init__(self):
        self.redis = RedisOperations()

    async def create_session(self, user_id: str, title: Optional[str] = None) -> SessionInfo:
        """创建新会话"""
        await self.redis.init()

        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "title": title or "新对话",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "model": "qwen-max",
            "kb_ids": "[]"  # JSON 字符串
        }

        # 保存会话元信息
        await self.redis.client.hset(f"session:{session_id}", mapping=session_data)

        # 添加到用户会话列表
        await self.redis.client.zadd(
            f"user:sessions:{user_id}",
            {session_id: int(datetime.now().timestamp())}
        )

        # 设置为活跃会话
        await self.redis.client.set(f"user:active_session:{user_id}", session_id)

        logger.info(f"Session created: {session_id} for user {user_id}")
        return SessionInfo(**{**session_data, "kb_ids": []})

    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[SessionInfo]:
        """获取用户的所有会话（按更新时间倒序）"""
        await self.redis.init()

        # 获取会话 ID 列表（倒序）
        session_ids = await self.redis.client.zrevrange(
            f"user:sessions:{user_id}",
            0,
            limit - 1
        )

        sessions = []
        for session_id in session_ids:
            session_data = await self.redis.client.hgetall(f"session:{session_id}")
            if session_data:
                session_data["kb_ids"] = eval(session_data.get("kb_ids", "[]"))
                sessions.append(SessionInfo(**session_data))

        return sessions

    async def get_session(self, session_id: str) -> Optional[SessionDetail]:
        """获取会话详情"""
        await self.redis.init()

        # 获取会话元信息
        session_data = await self.redis.client.hgetall(f"session:{session_id}")
        if not session_data:
            return None

        session_data["kb_ids"] = eval(session_data.get("kb_ids", "[]"))
        session_info = SessionInfo(**session_data)

        # 获取消息列表
        messages = await self.redis.lrange_json(f"session:messages:{session_id}", 0, -1)

        return SessionDetail(session=session_info, messages=messages)

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """删除会话"""
        await self.redis.init()

        # 验证会话属于该用户
        session_data = await self.redis.client.hget(f"session:{session_id}", "user_id")
        if session_data != user_id:
            return False

        # 删除会话数据
        await self.redis.client.delete(f"session:{session_id}")
        await self.redis.client.delete(f"session:messages:{session_id}")
        await self.redis.client.delete(f"session:summary:{session_id}")

        # 从用户会话列表移除
        await self.redis.client.zrem(f"user:sessions:{user_id}", session_id)

        logger.info(f"Session deleted: {session_id}")
        return True

    async def update_title(self, session_id: str, title: str, user_id: str) -> bool:
        """更新会话标题"""
        await self.redis.init()

        # 验证会话属于该用户
        session_data = await self.redis.client.hget(f"session:{session_id}", "user_id")
        if session_data != user_id:
            return False

        await self.redis.client.hset(f"session:{session_id}", "title", title)
        await self.redis.client.hset(f"session:{session_id}", "updated_at", datetime.now().isoformat())

        return True

    async def get_active_session(self, user_id: str) -> Optional[str]:
        """获取用户当前活跃会话"""
        await self.redis.init()
        return await self.redis.client.get(f"user:active_session:{user_id}")

    async def set_active_session(self, user_id: str, session_id: str) -> bool:
        """设置活跃会话"""
        await self.redis.init()

        # 验证会话存在
        session_data = await self.redis.client.hget(f"session:{session_id}", "user_id")
        if session_data != user_id:
            return False

        await self.redis.client.set(f"user:active_session:{user_id}", session_id)
        return True
```

**Step 3: 创建测试**

```python
# tests/gateway/services/test_session_service.py
import pytest
from apps.gateway.services.session_service import SessionService


@pytest.mark.asyncio
async def test_create_session():
    """测试创建会话"""
    service = SessionService()
    session = await service.create_session("user-test-001", "测试会话")

    assert session.session_id.startswith("sess-")
    assert session.user_id == "user-test-001"
    assert session.title == "测试会话"
    assert session.message_count == 0


@pytest.mark.asyncio
async def test_get_user_sessions():
    """测试获取用户会话列表"""
    service = SessionService()

    # 创建多个会话
    await service.create_session("user-test-002", "会话1")
    await service.create_session("user-test-002", "会话2")

    sessions = await service.get_user_sessions("user-test-002")
    assert len(sessions) >= 2
```

**Step 4: 运行测试**

Run: `pytest tests/gateway/services/test_session_service.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/gateway/models/session.py apps/gateway/services/session_service.py tests/gateway/services/test_session_service.py
git commit -m "feat: add session management service"
```

---

### Task 6: 创建会话管理路由

**Files:**
- Create: `apps/gateway/routers/sessions.py`
- Modify: `apps/gateway/main.py`

**Step 1: 创建会话路由**

```python
# apps/gateway/routers/sessions.py
"""会话管理路由"""
from fastapi import APIRouter, Request, HTTPException

from apps.gateway.models.session import (
    CreateSessionRequest, SessionInfo, SessionDetail,
    UpdateSessionTitleRequest
)
from apps.gateway.services.session_service import SessionService
from apps.shared.logger import LogManager

logger_manager = LogManager("sessions")
logger = logger_manager.get_logger()

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def get_user_id(req: Request) -> str:
    """从请求头获取用户 ID"""
    user_id = req.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not provided")
    return user_id


@router.post("", response_model=SessionInfo)
async def create_session(request: CreateSessionRequest, req: Request):
    """创建新会话"""
    user_id = get_user_id(req)

    if request.user_id != user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")

    service = SessionService()
    return await service.create_session(user_id, request.title)


@router.get("", response_model=list[SessionInfo])
async def list_sessions(req: Request, limit: int = 50):
    """获取用户的所有会话"""
    user_id = get_user_id(req)

    service = SessionService()
    return await service.get_user_sessions(user_id, limit)


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str, req: Request):
    """获取会话详情"""
    user_id = get_user_id(req)

    service = SessionService()
    session = await service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return session


@router.delete("/{session_id}")
async def delete_session(session_id: str, req: Request):
    """删除会话"""
    user_id = get_user_id(req)

    service = SessionService()
    success = await service.delete_session(session_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found or access denied")

    return {"success": True}


@router.put("/{session_id}/title")
async def update_session_title(session_id: str, request: UpdateSessionTitleRequest, req: Request):
    """更新会话标题"""
    user_id = get_user_id(req)

    service = SessionService()
    success = await service.update_title(session_id, request.title, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found or access denied")

    return {"success": True}


@router.post("/{session_id}/switch")
async def switch_session(session_id: str, req: Request):
    """切换活跃会话"""
    user_id = get_user_id(req)

    service = SessionService()
    success = await service.set_active_session(user_id, session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found or access denied")

    return {"success": True, "active_session": session_id}
```

**Step 2: 注册路由**

```python
# apps/gateway/main.py
from apps.gateway.routers import sessions

app.include_router(sessions.router, tags=["Sessions"])
```

**Step 3: Commit**

```bash
git add apps/gateway/routers/sessions.py apps/gateway/main.py
git commit -m "feat: add session management routes"
```

---

## Phase 4: 消息存储与上下文构建

### Task 7: 创建消息存储服务

**Files:**
- Create: `apps/gateway/services/message_service.py`

**Step 1: 创建消息服务**

```python
# apps/gateway/services/message_service.py
"""消息存储服务"""
from datetime import datetime
from typing import List

from apps.gateway.models.session import SessionMessage
from apps.shared.redis_client import RedisOperations
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("message_service")
logger = logger_manager.get_logger()

# 配置参数
WINDOW_SIZE = config.get("dependencies.redis.context.window_size", 10)
SUMMARY_THRESHOLD = config.get("dependencies.redis.context.summary_threshold", 20)
SUMMARY_INTERVAL = config.get("dependencies.redis.context.summary_interval", 10)


class MessageService:
    """消息服务"""

    def __init__(self):
        self.redis = RedisOperations()

    async def save_message(self, session_id: str, role: str, content: str) -> SessionMessage:
        """保存消息到会话"""
        await self.redis.init()

        message = SessionMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat()
        )

        # 保存消息
        await self.redis.rpush_json(f"session:messages:{session_id}", message.dict())

        # 更新会话元信息
        await self.redis.client.hincrby(f"session:{session_id}", "message_count", 1)
        await self.redis.client.hset(
            f"session:{session_id}",
            "updated_at",
            datetime.now().isoformat()
        )

        # 检查是否需要生成摘要
        message_count = int(await self.redis.client.hget(f"session:{session_id}", "message_count") or 0)
        if message_count % SUMMARY_INTERVAL == 0 and message_count > WINDOW_SIZE:
            # 标记需要生成摘要（异步处理）
            await self.redis.client.set(f"session:needs_summary:{session_id}", "1")

        return message

    async def get_context_messages(self, session_id: str) -> List[dict]:
        """获取用于 LLM 请求的上下文消息"""
        await self.redis.init()

        # 获取所有消息数量
        message_count = await self.redis.client.llen(f"session:messages:{session_id}")

        context = []

        # 如果消息超过阈值，添加摘要
        if message_count > SUMMARY_THRESHOLD:
            summary = await self.redis.client.get(f"session:summary:{session_id}")
            if summary:
                context.append({
                    "role": "system",
                    "content": f"【历史对话摘要】\n{summary}"
                })

        # 获取近期消息
        start_index = max(0, message_count - WINDOW_SIZE)
        recent_messages = await self.redis.lrange_json(
            f"session:messages:{session_id}",
            start_index,
            -1
        )

        # 转换为 LangChain 消息格式
        for msg in recent_messages:
            context.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        return context

    async def get_session_messages(self, session_id: str) -> List[SessionMessage]:
        """获取会话的所有消息"""
        await self.redis.init()
        messages = await self.redis.lrange_json(f"session:messages:{session_id}", 0, -1)
        return [SessionMessage(**msg) for msg in messages]
```

**Step 2: 创建测试**

```python
# tests/gateway/services/test_message_service.py
import pytest
from apps.gateway.services.message_service import MessageService


@pytest.mark.asyncio
async def test_save_and_get_messages():
    """测试保存和获取消息"""
    service = MessageService()

    # 保存消息
    await service.save_message("sess-test-001", "user", "你好")
    await service.save_message("sess-test-001", "assistant", "你好！")

    messages = await service.get_session_messages("sess-test-001")
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"


@pytest.mark.asyncio
async def test_context_messages():
    """测试获取上下文消息"""
    service = MessageService()

    # 模拟保存多条消息
    for i in range(15):
        await service.save_message("sess-test-002", "user", f"消息{i}")

    context = await service.get_context_messages("sess-test-002")
    # 应该只返回最近的 10 条
    assert len(context) <= 10
```

**Step 3: 运行测试**

Run: `pytest tests/gateway/services/test_message_service.py -v`

Expected: PASS

**Step 4: Commit**

```bash
git add apps/gateway/services/message_service.py tests/gateway/services/test_message_service.py
git commit -m "feat: add message storage service with context building"
```

---

### Task 8: 更新聊天路由集成会话

**Files:**
- Modify: `apps/gateway/routers/chat.py`
- Modify: `apps/gateway/models.py`

**Step 1: 更新聊天请求模型**

```python
# apps/gateway/models.py
# 在 ChatRequest 类中添加字段
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    stream: bool = Field(default=True, description="是否流式返回")
    enable_search: bool = Field(default=False, description="是否启用联网搜索")
    kb_ids: Optional[List[str]] = Field(default=None, description="知识库ID列表")

    # 新增字段
    session_id: Optional[str] = Field(default=None, description="会话ID（可选，不传则创建新会话）")
```

**Step 2: 更新聊天路由**

```python
# apps/gateway/routers/chat.py
# 添加导入
from apps.gateway.services.session_service import SessionService
from apps.gateway.services.message_service import MessageService

# 更新 chat_stream 函数
@router.post("/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """流式聊天接口"""
    user_id = req.state.session_id  # 从中间件获取
    session_id = request.session_id

    logger.info(f"Chat request: user={user_id}, session={session_id}, message={request.message[:50]}")

    # 处理会话
    session_service = SessionService()
    message_service = MessageService()

    if not session_id:
        # 创建新会话
        session = await session_service.create_session(user_id)
        session_id = session.session_id
    else:
        # 验证会话存在
        session = await session_service.get_session(session_id)
        if not session or session.session.user_id != user_id:
            return StreamingResponse(
                _error_stream("Session not found or access denied"),
                media_type="text/event-stream"
            )

    # 设置活跃会话
    await session_service.set_active_session(user_id, session_id)

    # 获取上下文消息
    context_messages = await message_service.get_context_messages(session_id)

    async def stream_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 流"""
        full_response = ""
        try:
            # 构建请求
            orchestrator_request = {
                "session_id": session_id,
                "user_id": user_id,
                "message": request.message,
                "chat_history": context_messages,  # 使用上下文消息
                "enable_search": request.enable_search,
                "kb_ids": request.kb_ids or [],
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    f"{ORCHESTRATOR_URL}/api/v1/chat",
                    json=orchestrator_request
                ) as response:
                    if response.status_code != 200:
                        error_msg = f"Orchestrator error: {response.status_code}"
                        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if line:
                            yield f"data: {line}\n\n"

                            # 收集完整响应用于保存
                            try:
                                data = json.loads(line)
                                if data.get("type") == "chunk":
                                    full_response += data.get("content", "")
                            except:
                                pass

        except httpx.ConnectError as e:
            error_msg = f"Cannot connect to Orchestrator at {ORCHESTRATOR_URL}"
            logger.error(f"{error_msg}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        finally:
            yield "data: [DONE]\n\n"

            # 保存消息到会话
            if full_response:
                await message_service.save_message(session_id, "user", request.message)
                await message_service.save_message(session_id, "assistant", full_response)

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id  # 返回新创建的 session_id
        }
    )


def _error_stream(message: str) -> AsyncGenerator[str, None]:
    """生成错误流"""
    async def gen():
        yield f"data: {json.dumps({'type': 'error', 'message': message})}\n\n"
        yield "data: [DONE]\n\n"
    return gen()
```

**Step 3: Commit**

```bash
git add apps/gateway/routers/chat.py apps/gateway/models.py
git commit -m "feat: integrate session management into chat flow"
```

---

## Phase 5: 长期记忆系统

### Task 9: 创建 Milvus 记忆 Collection

**Files:**
- Create: `scripts/init_memory_collection.py`

**Step 1: 创建初始化脚本**

```python
# scripts/init_memory_collection.py
"""初始化用户记忆向量 Collection"""
from pymilvus import (
    connections, Collection, FieldSchema, CollectionSchema,
    DataType, utility
)

from apps.shared.config_loader import ConfigLoader

config = ConfigLoader()
milvus_config = config.get("dependencies.milvus")

# 连接 Milvus
print(f"Connecting to Milvus at {milvus_config['host']}:{milvus_config['port']}...")
connections.connect(
    alias="default",
    host=milvus_config['host'],
    port=milvus_config['port']
)

# 定义 Schema
collection_name = "user_memories"

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=2048),
    FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="memory_type", dtype=DataType.VARCHAR, max_length=20),
    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
    FieldSchema(name="session_id", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="importance", dtype=DataType.FLOAT),
    FieldSchema(name="created_at", dtype=DataType.INT64),
]

schema = CollectionSchema(
    fields=fields,
    description="User long-term memories",
    enable_dynamic_field=True
)

# 检查是否存在
if utility.has_collection(collection_name):
    print(f"Collection '{collection_name}' already exists. Dropping...")
    utility.drop_collection(collection_name)

# 创建 Collection
print(f"Creating collection '{collection_name}'...")
collection = Collection(name=collection_name, schema=schema)

# 创建索引
print("Creating index on 'vector' field...")
index_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {"M": 16, "efConstruction": 256}
}
collection.create_index(field_name="vector", index_params=index_params)

print(f"Collection '{collection_name}' created successfully!")
print(f"Schema: {collection.schema}")
```

**Step 2: 运行初始化脚本**

Run: `python scripts/init_memory_collection.py`

Expected: `Collection 'user_memories' created successfully!`

**Step 3: Commit**

```bash
git add scripts/init_memory_collection.py
git commit -m "feat: add milvus memory collection initialization script"
```

---

### Task 6: 创建记忆服务

**Files:**
- Create: `apps/orchestrator/services/memory_service.py`
- Create: `apps/orchestrator/models/memory.py`

**Step 1: 定义记忆模型**

```python
# apps/orchestrator/models/memory.py
"""记忆相关模型"""
from pydantic import BaseModel, Field
from typing import List, Optional


class MemoryItem(BaseModel):
    """单个记忆项"""
    type: str = Field(..., pattern="^(fact|preference|context)$")
    content: str
    importance: float = Field(default=0.5, ge=0, le=1)


class MemoryExtraction(BaseModel):
    """记忆提取结果"""
    memories: List[MemoryItem]


class RetrievedMemory(BaseModel):
    """检索到的记忆"""
    content: str
    memory_type: str
    importance: float
    distance: float
```

**Step 2: 创建记忆服务**

```python
# apps/orchestrator/services/memory_service.py
"""长期记忆服务"""
import time
from typing import List, Optional

from pymilvus import Collection, connections

from apps.orchestrator.models.memory import MemoryItem, RetrievedMemory
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("memory_service")
logger = logger_manager.get_logger()

# 配置
COLLECTION_NAME = config.get("dependencies.redis.memory.collection_name", "user_memories")
IMPORTANCE_THRESHOLD = config.get("dependencies.redis.memory.importance_threshold", 0.5)
TOP_K = config.get("dependencies.redis.memory.retrieval_top_k", 3)

# 连接 Milvus
milvus_config = config.get("dependencies.milvus")
connections.connect(
    alias="default",
    host=milvus_config['host'],
    port=milvus_config['port']
)


class MemoryService:
    """记忆服务"""

    def __init__(self):
        self.collection = Collection(COLLECTION_NAME)
        self.collection.load()

    async def save_memory(
        self,
        user_id: str,
        memory: MemoryItem,
        session_id: str,
        embedding: List[float]
    ):
        """保存记忆"""
        entity = [
            [embedding],
            [user_id],
            [memory.type],
            [memory.content],
            [session_id],
            [memory.importance],
            [int(time.time())]
        ]

        self.collection.insert(entity)
        logger.info(f"Memory saved for user {user_id}: {memory.content[:50]}...")

    async def retrieve_memories(
        self,
        user_id: str,
        query_embedding: List[float],
        top_k: int = TOP_K
    ) -> List[RetrievedMemory]:
        """检索相关记忆"""
        results = self.collection.search(
            data=[query_embedding],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"ef": 32}},
            limit=top_k,
            expr=f"user_id == '{user_id}' and importance >= {IMPORTANCE_THRESHOLD}",
            output_fields=["content", "memory_type", "importance"]
        )

        memories = []
        for hit in results[0]:
            memories.append(RetrievedMemory(
                content=hit.entity.get("content"),
                memory_type=hit.entity.get("memory_type"),
                importance=hit.entity.get("importance"),
                distance=hit.distance
            ))

        return memories

    async def get_user_memories(self, user_id: str, limit: int = 100) -> List[dict]:
        """获取用户的所有记忆"""
        results = self.collection.query(
            expr=f"user_id == '{user_id}'",
            output_fields=["content", "memory_type", "importance", "created_at"],
            limit=limit
        )
        return results
```

**Step 3: 创建测试**

```python
# tests/orchestrator/services/test_memory_service.py
import pytest
from apps.orchestrator.services.memory_service import MemoryService
from apps.orchestrator.models.memory import MemoryItem


@pytest.mark.asyncio
async def test_save_and_retrieve_memory():
    """测试保存和检索记忆"""
    service = MemoryService()

    # 模拟 embedding
    embedding = [0.1] * 2048

    # 保存记忆
    memory = MemoryItem(
        type="fact",
        content="用户是后端开发工程师",
        importance=0.8
    )
    await service.save_memory("user-test-001", memory, "sess-test-001", embedding)

    # 检索记忆
    results = await service.retrieve_memories("user-test-001", embedding)
    assert len(results) > 0
    assert "后端开发工程师" in results[0].content
```

**Step 4: Commit**

```bash
git add apps/orchestrator/services/memory_service.py apps/orchestrator/models/memory.py tests/orchestrator/services/test_memory_service.py
git commit -m "feat: add long-term memory service with milvus"
```

---

### Task 11: 创建记忆提取服务

**Files:**
- Create: `apps/orchestrator/services/memory_extractor.py`

**Step 1: 创建记忆提取服务**

```python
# apps/orchestrator/services/memory_extractor.py
"""记忆提取服务"""
from typing import List

from apps.orchestrator.models.memory import MemoryExtraction, MemoryItem
from apps.shared.logger import LogManager

logger_manager = LogManager("memory_extractor")
logger = logger_manager.get_logger()


class MemoryExtractor:
    """记忆提取器"""

    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def extract_memories(
        self,
        user_message: str,
        ai_response: str,
        session_id: str
    ) -> List[MemoryItem]:
        """从对话中提取记忆"""

        conversation = f"""用户：{user_message}
AI：{ai_response}"""

        prompt = f"""分析以下对话，提取值得长期记忆的信息。

{conversation}

输出格式（JSON）：
{{
  "memories": [
    {{
      "type": "fact|preference|context",
      "content": "记忆内容",
      "importance": 0.8
    }}
  ]
}}

只输出 JSON，无其他内容。如果没有值得记忆的信息，返回空数组。"""

        try:
            response = await self.llm_client.complete(
                prompt,
                max_tokens=500,
                temperature=0.3
            )

            # 解析 JSON 响应
            import json
            result = json.loads(response)
            extraction = MemoryExtraction(**result)

            logger.info(f"Extracted {len(extraction.memories)} memories from session {session_id}")
            return extraction.memories

        except Exception as e:
            logger.error(f"Memory extraction error: {e}")
            return []
```

**Step 2: Commit**

```bash
git add apps/orchestrator/services/memory_extractor.py
git commit -m "feat: add memory extraction service"
```

---

### Task 12: 集成记忆到 Orchestrator

**Files:**
- Modify: `apps/orchestrator/graph/state.py`
- Modify: `apps/orchestrator/main.py`
- Modify: `apps/orchestrator/graph/nodes/rag_retriever.py`

**Step 1: 更新状态定义**

```python
# apps/orchestrator/graph/state.py
# 在 AgentState 类中添加字段

class AgentState(MessagesState):
    # ... 现有字段 ...

    # 新增：记忆相关
    retrieved_memories: List[dict]  # 检索到的相关记忆
```

**Step 2: 创建上下文构建节点**

```python
# apps/orchestrator/graph/nodes/context_builder.py
"""上下文构建节点"""
from typing import List

from langchain_core.messages import SystemMessage

from apps.orchestrator.graph.state import AgentState
from apps.orchestrator.services.memory_service import MemoryService
from apps.shared.logger import LogManager

logger_manager = LogManager("context_builder")
logger = logger_manager.get_logger()


async def build_context(state: AgentState) -> AgentState:
    """构建包含记忆的上下文"""

    user_id = state.get("user_id")
    user_message = state.get("user_message", "")

    # 获取用户画像（从 Redis 获取用户信息）
    # TODO: 从 Redis 获取用户信息

    # 检索相关记忆
    retrieved_memories = []
    if user_id and user_message:
        memory_service = MemoryService()

        # 获取 query embedding
        # TODO: 调用 embedding 服务
        query_embedding = [0.1] * 2048  # 临时占位

        memories = await memory_service.retrieve_memories(user_id, query_embedding)

        if memories:
            memory_text = "\n".join([f"- {m.content}" for m in memories])
            retrieved_memories = [m.dict() for m in memories]

            # 添加到系统消息
            system_content = f"""【相关记忆】
{memory_text}

请根据以上记忆和用户的问题进行回答。"""

            # 插入到消息列表开头
            state["messages"] = [SystemMessage(content=system_content)] + list(state.get("messages", []))

    state["retrieved_memories"] = retrieved_memories
    logger.info(f"Built context with {len(retrieved_memories)} memories")

    return state
```

**Step 3: 更新图流程**

```python
# apps/orchestrator/graph/agent_graph.py
# 添加上下文构建节点

from apps.orchestrator.graph.nodes.context_builder import build_context

# 在图中添加节点
graph.add_node("context_builder", build_context)

# 更新路由：用户消息 → 上下文构建 → 路由判断
graph.set_entry_point("context_builder")
```

**Step 4: Commit**

```bash
git add apps/orchestrator/graph/state.py apps/orchestrator/graph/nodes/context_builder.py apps/orchestrator/graph/agent_graph.py
git commit -m "feat: integrate memory retrieval into orchestrator graph"
```

---

## Phase 6: 前端实现

### Task 13: 创建用户认证相关组件

**Files:**
- Create: `apps/web-ui/src/api/auth.js`
- Create: `apps/web-ui/src/components/auth/NicknameModal.jsx`

**Step 1: 创建认证 API**

```javascript
// apps/web-ui/src/api/auth.js
import { API_BASE_URL } from './config';

export const authApi = {
  // 注册/登录
  register: async (nickname) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nickname })
    });
    return response.json();
  },

  // 获取当前用户
  getMe: async (userId) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      headers: { 'X-User-Id': userId }
    });
    return response.json();
  },

  // 更新偏好设置
  updatePreferences: async (userId, preferences) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/preferences`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': userId
      },
      body: JSON.stringify(preferences)
    });
    return response.json();
  }
};
```

**Step 2: 创建昵称输入弹窗**

```jsx
// apps/web-ui/src/components/auth/NicknameModal.jsx
import { useState } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { authApi } from '../../api/auth';

const USER_STORAGE_KEY = 'rshanygen_user';

export default function NicknameModal({ onComplete }) {
  const [nickname, setNickname] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!nickname.trim() || isLoading) return;

    setIsLoading(true);
    try {
      const result = await authApi.register(nickname.trim());

      // 保存到 LocalStorage
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({
        userId: result.user_id,
        nickname: result.nickname
      }));

      onComplete(result);
    } catch (error) {
      console.error('Registration error:', error);
      alert('注册失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-bg-card-dark rounded-2xl p-6 max-w-md w-full mx-4 shadow-elevation-3">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-text-primary dark:text-text-primary-dark">
            欢迎使用
          </h2>
        </div>

        <p className="text-text-muted dark:text-text-secondary-dark mb-6">
          请输入您的昵称开始使用
        </p>

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="输入昵称（1-20个字符）"
            className="w-full px-4 py-3 rounded-xl border border-border dark:border-border-dark
                     bg-white dark:bg-bg-input-dark text-text-primary dark:text-text-primary-dark
                     focus:ring-2 focus:ring-primary focus:border-transparent
                     transition-all duration-200"
            maxLength={20}
            autoFocus
          />

          <div className="flex gap-3 mt-4">
            <button
              type="submit"
              disabled={!nickname.trim() || isLoading}
              className="flex-1 py-3 px-6 rounded-xl bg-gradient-to-r from-primary to-primary-600
                       text-white font-medium shadow-glow-sm hover:shadow-glow-md
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200"
            >
              {isLoading ? '注册中...' : '开始使用'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add apps/web-ui/src/api/auth.js apps/web-ui/src/components/auth/NicknameModal.jsx
git commit -m "feat: add user authentication modal component"
```

---

### Task 14: 创建会话管理组件

**Files:**
- Create: `apps/web-ui/src/api/sessions.js`
- Create: `apps/web-ui/src/components/session/SessionList.jsx`
- Create: `apps/web-ui/src/components/session/SessionItem.jsx`

**Step 1: 创建会话 API**

```javascript
// apps/web-ui/src/api/sessions.js
import { API_BASE_URL } from './config';

const getHeaders = (userId) => ({
  'Content-Type': 'application/json',
  'X-User-Id': userId
});

export const sessionsApi = {
  // 获取会话列表
  list: async (userId) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/sessions`, {
      headers: getHeaders(userId)
    });
    return response.json();
  },

  // 创建会话
  create: async (userId, title) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/sessions`, {
      method: 'POST',
      headers: getHeaders(userId),
      body: JSON.stringify({ user_id: userId, title })
    });
    return response.json();
  },

  // 获取会话详情
  get: async (userId, sessionId) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}`, {
      headers: getHeaders(userId)
    });
    return response.json();
  },

  // 删除会话
  delete: async (userId, sessionId) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: getHeaders(userId)
    });
    return response.json();
  },

  // 更新标题
  updateTitle: async (userId, sessionId, title) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/title`, {
      method: 'PUT',
      headers: getHeaders(userId),
      body: JSON.stringify({ title })
    });
    return response.json();
  },

  // 切换会话
  switch: async (userId, sessionId) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/switch`, {
      method: 'POST',
      headers: getHeaders(userId)
    });
    return response.json();
  }
};
```

**Step 2: 创建会话列表组件**

```jsx
// apps/web-ui/src/components/session/SessionList.jsx
import { useEffect, useState } from 'react';
import { PlusIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import { sessionsApi } from '../../api/sessions';
import SessionItem from './SessionItem';

const USER_STORAGE_KEY = 'rshanygen_user';

export default function SessionList({ currentSessionId, onSessionChange, onNewSession }) {
  const [sessions, setSessions] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const loadSessions = async () => {
    const userData = JSON.parse(localStorage.getItem(USER_STORAGE_KEY) || '{}');
    if (!userData.userId) return;

    try {
      const data = await sessionsApi.list(userData.userId);
      setSessions(data);
    } catch (error) {
      console.error('Load sessions error:', error);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [currentSessionId]);

  const handleDelete = async (sessionId) => {
    if (!confirm('确定要删除这个会话吗？')) return;

    const userData = JSON.parse(localStorage.getItem(USER_STORAGE_KEY) || '{}');
    try {
      await sessionsApi.delete(userData.userId, sessionId);
      await loadSessions();

      if (currentSessionId === sessionId) {
        onNewSession();
      }
    } catch (error) {
      console.error('Delete session error:', error);
    }
  };

  const handleUpdateTitle = async (sessionId, newTitle) => {
    const userData = JSON.parse(localStorage.getItem(USER_STORAGE_KEY) || '{}');
    try {
      await sessionsApi.updateTitle(userData.userId, sessionId, newTitle);
      setEditingId(null);
      await loadSessions();
    } catch (error) {
      console.error('Update title error:', error);
    }
  };

  return (
    <div className="h-full flex flex-col bg-bg-secondary dark:bg-bg-secondary-dark border-r border-border dark:border-border-dark">
      {/* 新建会话按钮 */}
      <div className="p-3">
        <button
          onClick={onNewSession}
          className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl
                   bg-gradient-to-r from-primary to-primary-600 text-white
                   shadow-glow-sm hover:shadow-glow-md transition-all duration-200"
        >
          <PlusIcon className="w-5 h-5" />
          <span className="font-medium">新建对话</span>
        </button>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {sessions.map((session) => (
          <SessionItem
            key={session.session_id}
            session={session}
            isActive={session.session_id === currentSessionId}
            onClick={() => onSessionChange(session.session_id)}
            onDelete={() => handleDelete(session.session_id)}
            isEditing={editingId === session.session_id}
            onEditStart={() => {
              setEditingId(session.session_id);
              setEditTitle(session.title);
            }}
            onEditCancel={() => setEditingId(null)}
            onEditSave={() => handleUpdateTitle(session.session_id, editTitle)}
            editTitle={editTitle}
            onEditTitleChange={setEditTitle}
          />
        ))}
      </div>
    </div>
  );
}
```

**Step 3: 创建会话项组件**

```jsx
// apps/web-ui/src/components/session/SessionItem.jsx
import { CheckIcon, XIcon, TrashIcon, PencilIcon } from '@heroicons/react/24/outline';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

export default function SessionItem({
  session,
  isActive,
  onClick,
  onDelete,
  isEditing,
  onEditStart,
  onEditCancel,
  onEditSave,
  editTitle,
  onEditTitleChange
}) {
  if (isEditing) {
    return (
      <div className="flex items-center gap-1 px-3 py-2 mb-1 rounded-lg bg-bg-tertiary dark:bg-bg-tertiary-dark">
        <input
          type="text"
          value={editTitle}
          onChange={(e) => onEditTitleChange(e.target.value)}
          className="flex-1 px-2 py-1 text-sm bg-white dark:bg-bg-input-dark rounded border border-border dark:border-border-dark"
          autoFocus
        />
        <button
          onClick={onEditSave}
          className="p-1 text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
        >
          <CheckIcon className="w-4 h-4" />
        </button>
        <button
          onClick={onEditCancel}
          className="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
        >
          <XIcon className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={`group relative flex items-center gap-3 px-3 py-2.5 mb-1 rounded-xl cursor-pointer transition-all duration-200 ${
        isActive
          ? 'bg-primary/10 text-primary dark:bg-primary/20'
          : 'hover:bg-bg-tertiary dark:hover:bg-bg-tertiary-dark text-text-primary dark:text-text-primary-dark'
      }`}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{session.title || '新对话'}</p>
        <p className="text-xs text-text-muted dark:text-text-secondary-dark/70 mt-0.5">
          {formatDistanceToNow(new Date(session.updated_at), {
            addSuffix: true,
            locale: zhCN
          })}
        </p>
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onEditStart();
          }}
          className="p-1.5 text-text-muted hover:text-text-primary hover:bg-bg-tertiary dark:hover:bg-bg-tertiary-dark rounded-lg transition-colors"
        >
          <PencilIcon className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="p-1.5 text-text-muted hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
        >
          <TrashIcon className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
```

**Step 4: 安装 date-fns**

Run: `cd apps/web-ui && npm install date-fns`

**Step 5: Commit**

```bash
git add apps/web-ui/src/api/sessions.js apps/web-ui/src/components/session/SessionList.jsx apps/web-ui/src/components/session/SessionItem.jsx
git commit -m "feat: add session list components"
```

---

### Task 15: 更新主页面集成会话和认证

**Files:**
- Modify: `apps/web-ui/src/pages/ChatPage.jsx`
- Modify: `apps/web-ui/src/hooks/useChatStream.js`

**Step 1: 更新 useChatStream hook**

```javascript
// apps/web-ui/src/hooks/useChatStream.js
// 在 send 函数中添加 session_id 处理

export function useChatStream() {
  // ... 现有代码 ...

  const send = useCallback(async (message, options = {}) => {
    // ... 现有代码 ...

    // 添加 session_id
    const requestBody = {
      message,
      stream: true,
      enable_search: options.enableSearch || false,
      kb_ids: options.kbIds || [],
      session_id: options.sessionId || null  // 新增
    };

    // ... 其余代码 ...
  }, [/* 依赖 */]);

  return { send };
}
```

**Step 2: 更新 ChatPage 集成会话和认证**

```jsx
// apps/web-ui/src/pages/ChatPage.jsx
import { useState, useCallback, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useChatStream } from '../hooks/useChatStream';
import { useSkills } from '../hooks/useSkills';
import { sessionsApi } from '../api/sessions';
import NicknameModal from '../components/auth/NicknameModal';
import SessionList from '../components/session/SessionList';
import ThinkingIndicator from '../components/chat/ThinkingIndicator';
import KbSelector from '../components/chat/KbSelector';
import logo from '../assets/logo.png';

const USER_STORAGE_KEY = 'rshanygen_user';

export default function ChatPage() {
  // 用户状态
  const [userData, setUserData] = useState(null);
  const [showNicknameModal, setShowNicknameModal] = useState(false);

  // 会话状态
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [showSessions, setShowSessions] = useState(true);

  // 聊天状态
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingContent, setThinkingContent] = useState('');
  const [enableSearch, setEnableSearch] = useState(false);
  const [selectedKbs, setSelectedKbs] = useState([]);
  const [copiedId, setCopiedId] = useState(null);

  const { send } = useChatStream();
  const { enabledSkills } = useSkills();
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const isComposing = useRef(false);

  // 初始化：检查用户登录
  useEffect(() => {
    const stored = localStorage.getItem(USER_STORAGE_KEY);
    if (stored) {
      setUserData(JSON.parse(stored));
    } else {
      setShowNicknameModal(true);
    }
  }, []);

  // 加载会话列表
  useEffect(() => {
    if (userData) {
      loadSessions();
    }
  }, [userData]);

  const loadSessions = async () => {
    try {
      const data = await sessionsApi.list(userData.userId);
      setSessions(data);

      // 如果有活跃会话且当前没有会话，加载最新的会话
      if (data.length > 0 && !currentSessionId) {
        // 这里可以调用 API 获取活跃会话，暂时使用最新的
        switchToSession(data[0].session_id, data[0]);
      }
    } catch (error) {
      console.error('Load sessions error:', error);
    }
  };

  const switchToSession = async (sessionId, sessionData) => {
    setCurrentSessionId(sessionId);

    if (sessionData && sessionData.messages) {
      setMessages(sessionData.messages);
    } else {
      // 加载会话详情
      try {
        const detail = await sessionsApi.get(userData.userId, sessionId);
        setMessages(detail.messages || []);
      } catch (error) {
        console.error('Load session error:', error);
      }
    }
  };

  const handleNewSession = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setInputValue('');
  };

  const handleSend = useCallback(async () => {
    const message = inputValue.trim();
    if (!message || isLoading) return;

    // 添加用户消息
    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    setIsLoading(true);
    setThinkingContent('思考中...');

    let accumulatedContent = '';
    let aiMsgId = null;
    let returnedSessionId = null;

    const hasStartedRef = { current: false };

    try {
      await send(message, {
        sessionId: currentSessionId,
        enableSearch: enableSearch,
        kbIds: selectedKbs.map(kb => kb.kb_id),
        onThinking: (content) => {
          if (!hasStartedRef.current) {
            setThinkingContent(content);
          }
        },
        onChunk: (content) => {
          accumulatedContent += content;

          if (!aiMsgId) {
             hasStartedRef.current = true;
             setThinkingContent('');

             aiMsgId = Date.now() + 1;
             const aiMsg = {
               id: aiMsgId,
               role: 'assistant',
               content: '',
               timestamp: new Date().toISOString(),
             };
             setMessages(prev => [...prev, aiMsg]);
          }

          setMessages(prev => prev.map(msg =>
            msg.id === aiMsgId
              ? { ...msg, content: accumulatedContent }
              : msg
          ));
        },
        onDone: () => {
          setIsLoading(false);
          setThinkingContent('');
          hasStartedRef.current = false;

          // 更新会话 ID（如果是新会话）
          if (returnedSessionId && returnedSessionId !== currentSessionId) {
            setCurrentSessionId(returnedSessionId);
            loadSessions();
          }
        },
        onError: (errorMsg) => {
          // ... 错误处理 ...
        },
        onSessionId: (sid) => {
          returnedSessionId = sid;
        }
      });
    } catch (error) {
      // ... 错误处理 ...
    }
  }, [inputValue, isLoading, send, enableSearch, selectedKbs, currentSessionId, userData]);

  // ... 其余代码保持不变 ...

  return (
    <div className="h-full flex bg-bg-primary dark:bg-bg-dark transition-colors duration-200">
      {/* 左侧会话列表 */}
      {showSessions && (
        <div className="w-72 flex-shrink-0">
          <SessionList
            currentSessionId={currentSessionId}
            onSessionChange={(sessionId) => switchToSession(sessionId)}
            onNewSession={handleNewSession}
          />
        </div>
      )}

      {/* 右侧聊天区域 */}
      <div className="flex-1 flex flex-col">
        {/* 顶部栏 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border dark:border-border-dark">
          <button
            onClick={() => setShowSessions(!showSessions)}
            className="p-2 hover:bg-bg-tertiary dark:hover:bg-bg-tertiary-dark rounded-lg"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="font-medium text-text-primary dark:text-text-primary-dark">
            {userData?.nickname || '聊天'}
          </span>
        </div>

        {/* 聊天内容区域 */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* ... 现有消息渲染代码 ... */}
        </div>

        {/* 输入区域 */}
        <div className="p-4 md:p-6">
          <KbSelector selectedKbs={selectedKbs} onChange={setSelectedKbs} />
          {/* ... 现有输入框代码 ... */}
        </div>
      </div>

      {/* 昵称输入弹窗 */}
      {showNicknameModal && (
        <NicknameModal
          onComplete={(result) => {
            setUserData({ userId: result.user_id, nickname: result.nickname });
            localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({
              userId: result.user_id,
              nickname: result.nickname
            }));
            setShowNicknameModal(false);
          }}
        />
      )}
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add apps/web-ui/src/pages/ChatPage.jsx apps/web-ui/src/hooks/useChatStream.js
git commit -m "feat: integrate session management and auth into chat page"
```

---

## Phase 7: 摘要生成与记忆提取（异步任务）

### Task 16: 创建摘要生成服务

**Files:**
- Create: `apps/orchestrator/services/summary_generator.py`

**Step 1: 创建摘要生成服务**

```python
# apps/orchestrator/services/summary_generator.py
"""会话摘要生成服务"""
from typing import List

from apps.shared.redis_client import RedisOperations
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("summary_generator")
logger = logger_manager.get_logger()

WINDOW_SIZE = config.get("dependencies.redis.context.window_size", 10)


class SummaryGenerator:
    """摘要生成器"""

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.redis = RedisOperations()

    async def generate_summary(self, session_id: str) -> str:
        """生成会话摘要"""
        await self.redis.init()

        # 获取需要摘要的消息（排除最近的窗口消息）
        all_messages = await self.redis.lrange_json(f"session:messages:{session_id}", 0, -1)
        if len(all_messages) <= WINDOW_SIZE:
            return ""

        # 获取需要摘要的消息（从头到窗口大小之前）
        messages_to_summarize = all_messages[:-WINDOW_SIZE]

        # 格式化消息
        formatted = []
        for msg in messages_to_summarize:
            role = "用户" if msg["role"] == "user" else "AI"
            formatted.append(f"{role}: {msg['content']}")

        conversation = "\n".join(formatted)

        prompt = f"""请将以下对话摘要为一到两句话，保留关键信息：

{conversation}

摘要："""

        try:
            summary = await self.llm_client.complete(
                prompt,
                max_tokens=200,
                temperature=0.5
            )

            # 保存摘要
            await self.redis.client.set(f"session:summary:{session_id}", summary)

            logger.info(f"Summary generated for session {session_id}: {summary[:50]}...")
            return summary

        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return ""
```

**Step 2: Commit**

```bash
git add apps/orchestrator/services/summary_generator.py
git commit -m "feat: add session summary generator service"
```

---

### Task 17: 创建后台任务处理器

**Files:**
- Create: `apps/orchestrator/services/background_tasks.py`

**Step 1: 创建后台任务服务**

```python
# apps/orchestrator/services/background_tasks.py
"""后台异步任务处理"""
import asyncio

from apps.orchestrator.services.summary_generator import SummaryGenerator
from apps.orchestrator.services.memory_extractor import MemoryExtractor
from apps.orchestrator.services.memory_service import MemoryService
from apps.shared.redis_client import RedisOperations
from apps.shared.logger import LogManager

logger_manager = LogManager("background_tasks")
logger = logger_manager.get_logger()


class BackgroundTaskProcessor:
    """后台任务处理器"""

    def __init__(self, llm_client, embedding_client):
        self.llm_client = llm_client
        self.embedding_client = embedding_client
        self.summary_generator = SummaryGenerator(llm_client)
        self.memory_extractor = MemoryExtractor(llm_client)
        self.memory_service = MemoryService()
        self.redis = RedisOperations()
        self.running = False

    async def start(self):
        """启动后台处理器"""
        self.running = True
        logger.info("Background task processor started")

        # 启动多个处理任务
        await asyncio.gather(
            self._process_summaries(),
            self._process_memory_extractions(),
        )

    async def stop(self):
        """停止后台处理器"""
        self.running = False
        logger.info("Background task processor stopped")

    async def _process_summaries(self):
        """处理摘要生成任务"""
        while self.running:
            try:
                await self.redis.init()

                # 扫描需要生成摘要的会话
                # 这里使用简单的扫描，生产环境可以用 Redis Streams 或任务队列
                keys = await self.redis.client.keys("session:needs_summary:*")

                for key in keys:
                    session_id = key.split(":")[-1]

                    # 检查是否真的需要摘要
                    message_count = await self.redis.client.hget(f"session:{session_id}", "message_count")
                    if not message_count:
                        await self.redis.client.delete(key)
                        continue

                    # 生成摘要
                    await self.summary_generator.generate_summary(session_id)
                    await self.redis.client.delete(key)

                # 等待一段时间再检查
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Summary processing error: {e}")
                await asyncio.sleep(10)

    async def _process_memory_extractions(self):
        """处理记忆提取任务"""
        # TODO: 实现记忆提取的后台处理
        # 可以在消息保存时标记需要提取，然后在这里批量处理
        pass
```

**Step 2: 在 Orchestrator 中启动后台任务**

```python
# apps/orchestrator/main.py
# 添加后台任务处理器

from apps.orchestrator.services.background_tasks import BackgroundTaskProcessor

# 在 startup 事件中启动
@app.on_event("startup")
async def startup_event():
    # ... 现有代码 ...

    # 启动后台任务处理器
    global background_processor
    background_processor = BackgroundTaskProcessor(llm_client, embedding_client)
    asyncio.create_task(background_processor.start())

# 在 shutdown 事件中停止
@app.on_event("shutdown")
async def shutdown_event():
    # ... 现有代码 ...

    if background_processor:
        await background_processor.stop()
```

**Step 3: Commit**

```bash
git add apps/orchestrator/services/background_tasks.py apps/orchestrator/main.py
git commit -m "feat: add background task processor for summaries"
```

---

## Phase 8: 最终集成与测试

### Task 18: 端到端测试

**Files:**
- Create: `tests/integration/test_conversation_flow.py`

**Step 1: 创建集成测试**

```python
# tests/integration/test_conversation_flow.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport

from apps.gateway.main import app as gateway_app
from apps.orchestrator.main import app as orchestrator_app


@pytest.mark.asyncio
async def test_complete_conversation_flow():
    """测试完整的对话流程"""

    transport = ASGITransport(app=gateway_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. 注册用户
        response = await client.post(
            "/api/v1/auth/register",
            json={"nickname": "测试用户"}
        )
        assert response.status_code == 200
        user_data = response.json()
        user_id = user_data["user_id"]

        # 2. 创建会话
        response = await client.post(
            "/api/v1/sessions",
            json={"user_id": user_id, "title": "测试会话"},
            headers={"X-User-Id": user_id}
        )
        assert response.status_code == 200
        session = response.json()
        session_id = session["session_id"]

        # 3. 发送消息
        response = await client.post(
            "/api/v1/chat/stream",
            json={
                "message": "你好",
                "session_id": session_id
            },
            headers={"X-User-Id": user_id}
        )
        assert response.status_code == 200

        # 4. 获取会话详情验证消息保存
        response = await client.get(
            f"/api/v1/sessions/{session_id}",
            headers={"X-User-Id": user_id}
        )
        assert response.status_code == 200
        session_detail = response.json()
        assert len(session_detail["messages"]) >= 2  # 用户 + AI
```

**Step 2: 运行集成测试**

Run: `pytest tests/integration/test_conversation_flow.py -v`

Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_conversation_flow.py
git commit -m "test: add end-to-end conversation flow test"
```

---

### Task 19: 更新配置并添加环境变量

**Files:**
- Create: `.env.example`

**Step 1: 创建环境变量示例**

```bash
# .env.example

# Redis
REDIS_HOST=192.168.1.248
REDIS_PORT=6379
REDIS_DB=0

# Milvus
MILVUS_HOST=192.168.1.248
MILVUS_PORT=19530

# Admin
ADMIN_SECRET_PHRASE=your_admin_secret_here

# 上下文配置
CONTEXT_WINDOW_SIZE=10
CONTEXT_SUMMARY_THRESHOLD=20
CONTEXT_SUMMARY_INTERVAL=10

# 记忆配置
MEMORY_RETRIEVAL_TOP_K=3
MEMORY_IMPORTANCE_THRESHOLD=0.5
```

**Step 2: Commit**

```bash
git add .env.example
git commit -m "chore: add environment variables example"
```

---

### Task 20: 更新 README 文档

**Files:**
- Modify: `README.md`

**Step 1: 添加功能说明**

```markdown
# rshAnyGen

## 新增功能

### 多轮对话与历史会话管理
- 支持创建和管理多个历史会话
- 会话列表侧边栏，快速切换对话
- 会话标题自动生成和手动编辑
- 会话删除功能

### 长期记忆系统
- AI 自动记住用户偏好和重要信息
- 语义检索式记忆，跨会话提供个性化体验
- 记忆提取和存储到 Milvus 向量库

### 用户管理
- 首次访问输入昵称创建账户
- 基于 IP 防重复注册
- Admin 暗语登录（配置文件设置）

## 快速开始

### 1. 安装依赖
\`\`\`bash
pip install -r apps/gateway/requirements.txt
pip install -r apps/orchestrator/requirements.txt
cd apps/web-ui && npm install
\`\`\`

### 2. 初始化数据库
\`\`\`bash
python scripts/init_memory_collection.py
\`\`\`

### 3. 启动服务
\`\`\`bash
./scripts/dev.sh
\`\`\`

### 4. 访问应用
- Web UI: http://localhost:9300
- API 文档: http://localhost:9301/docs
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with new features"
```

---

## 完成总结

实施完成后，系统将具备：

1. **用户管理系统**
   - 昵称注册/登录
   - IP 防重复注册
   - Admin 暗语登录

2. **会话管理**
   - 创建/删除/切换会话
   - 会话列表侧边栏
   - 会话标题编辑
   - 消息持久化存储

3. **上下文管理**
   - 混合模式（近期消息 + 历史摘要）
   - 可配置的窗口大小和摘要阈值
   - 异步摘要生成

4. **长期记忆**
   - 对话记忆自动提取
   - 语义检索记忆
   - 记忆注入到系统提示

5. **前端体验**
   - Claude 风格的侧边栏
   - 流畅的会话切换
   - 昵称输入弹窗
