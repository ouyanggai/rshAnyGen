# 多轮对话与长期记忆系统设计文档

**日期**: 2025-01-22
**目标**: 实现类似 Claude Web 版的多轮对话、历史会话管理和长期记忆功能

---

## 一、需求概述

### 1.1 核心需求
- **会话历史管理**: 用户可查看、切换、管理多个历史会话
- **多轮对话能力**: 在同一会话内保持上下文连贯性
- **长期记忆**: AI能记住用户的偏好和重要信息，跨会话提供个性化体验
- **上下文压缩**: 使用混合模式避免 Token 爆炸

### 1.2 用户管理策略
- 首次访问时输入昵称创建用户
- 基于 IP 地址防重复注册（同IP更新昵称）
- Admin 使用暗语登录，固定权限

### 1.3 技术选型
- **存储**: Redis @ 192.168.1.248:6379
- **向量检索**: Milvus @ 192.168.1.248:19530
- **上下文策略**: 混合模式（近期消息 + 历史摘要）

---

## 二、整体架构

### 2.1 三层记忆架构

```
┌─────────────────────────────────────────────────────────────┐
│                        应用层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  会话列表UI  │  │  聊天界面UI  │  │  用户设置UI  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        网关层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  用户认证    │  │  会话管理    │  │  消息路由    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                       存储层                                 │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │      Redis              │  │      Milvus             │  │
│  │  - 用户信息             │  │  - 语义记忆向量         │  │
│  │  - 会话元数据           │  │  - 记忆检索             │  │
│  │  - 消息历史             │  │                         │  │
│  │  - 历史摘要             │  │                         │  │
│  └─────────────────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户发送消息
    ↓
[Gateway] 验证 user_id，获取 session_id
    ↓
[上下文构建器]
    ├─ 用户画像 (Redis Hash)
    ├─ 相关记忆 (Milvus 检索)
    ├─ 历史摘要 (Redis String)
    └─ 近期消息 (Redis List, 最近10条)
    ↓
[Orchestrator] 构建请求 → LLM 流式生成
    ↓
[Gateway] 返回流式响应
    ↓
[后台任务]
    ├─ 保存消息到 Redis
    ├─ 判断是否生成摘要
    ├─ 提取长期记忆 → Milvus
    └─ 更新会话时间戳
```

---

## 三、用户管理系统

### 3.1 Redis 数据结构

```python
# 用户信息 (Hash)
user:{user_id} = {
    "user_id": "uuid-xxx",
    "nickname": "张三",
    "ip_address": "192.168.1.100",
    "created_at": "2025-01-21T10:00:00Z",
    "last_seen": "2025-01-21T15:30:00Z",
    "preferences": {
        "default_model": "qwen-max",
        "temperature": 0.7,
        "default_search": false
    }
}

# IP → user_id 映射 (String, 防重复注册)
ip:user:{ip_address} = "user_id"

# Admin 暗语 (配置)
admin:secret = "your_secret_phrase"
```

### 3.2 注册/登录流程

```
用户首次访问
    ↓
检测 Cookie 中是否有 user_id
    ├─ 有 → 验证用户是否存在
    │        ├─ 存在 → 直接登录
    │        └─ 不存在 → 重新注册
    └─ 无 → 检测 IP 是否已注册
             ├─ 已注册 → 更新昵称，返回现有 user_id
             └─ 未注册 → 创建新用户
```

### 3.3 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/auth/me` | 获取当前用户信息 |
| POST | `/api/v1/auth/register` | 注册/登录（传入昵称） |
| PUT | `/api/v1/auth/preferences` | 更新用户偏好设置 |

**请求示例**：
```json
POST /api/v1/auth/register
{
  "nickname": "张三"
}

// 响应
{
  "user_id": "uuid-xxx",
  "nickname": "张三",
  "is_new": false
}
```

---

## 四、会话历史管理

### 4.1 Redis 数据结构

```python
# ============ 会话管理 ============
# 会话元信息 (Hash)
session:{session_id} = {
    "session_id": "sess-xxx",
    "user_id": "user-xxx",
    "title": "如何使用 Python",
    "created_at": "2025-01-21T10:00:00Z",
    "updated_at": "2025-01-21T15:30:00Z",
    "message_count": 12,
    "model": "qwen-max",
    "kb_ids": ["kb_001", "kb_002"]
}

# 会话消息列表 (List)
session:messages:{session_id} = [
    {"role": "user", "content": "你好", "timestamp": "..."},
    {"role": "assistant", "content": "你好！", "timestamp": "..."},
    ...
]

# 会话摘要 (String)
session:summary:{session_id} = "用户询问了Python的使用方法..."

# ============ 用户关联 ============
# 用户所有会话 (Sorted Set，按更新时间排序)
user:sessions:{user_id} = [
    ("session_1", 1737454200),
    ("session_2", 1737450000),
    ...
]

# 用户当前活跃会话
user:active_session:{user_id} = "session_3"
```

### 4.2 上下文构建策略（混合模式）

```python
# 配置参数
WINDOW_SIZE = 10           # 近期完整消息数量
SUMMARY_THRESHOLD = 20     # 触发摘要的消息阈值
SUMMARY_INTERVAL = 10      # 每N条消息检查一次

def build_context(session_id: str) -> List[dict]:
    """构建 LLM 请求的上下文"""
    all_messages = redis.lrange(f"session:messages:{session_id}", 0, -1)
    total_count = len(all_messages)

    context = []

    # 1. 如果消息超过阈值，添加摘要
    if total_count > SUMMARY_THRESHOLD:
        summary = redis.get(f"session:summary:{session_id}")
        if summary:
            context.append({
                "role": "system",
                "content": f"【历史对话摘要】\n{summary}"
            })

    # 2. 添加近期完整消息
    start_index = max(0, total_count - WINDOW_SIZE)
    recent_messages = all_messages[start_index:]
    context.extend(recent_messages)

    return context
```

### 4.3 会话标题生成

```python
async def generate_title(session_id: str, first_message: str):
    """根据首条消息生成会话标题"""
    prompt = f"""为以下用户消息生成一个简短的标题（不超过10个字）：

用户消息：{first_message}

标题："""
    title = await llm_complete(prompt, max_tokens=50)
    redis.hset(f"session:{session_id}", "title", title)
```

### 4.4 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/sessions` | 获取用户所有会话列表 |
| POST | `/api/v1/sessions` | 创建新会话 |
| GET | `/api/v1/sessions/{id}` | 获取会话详情和消息 |
| DELETE | `/api/v1/sessions/{id}` | 删除会话 |
| PUT | `/api/v1/sessions/{id}/title` | 更新会话标题 |
| POST | `/api/v1/sessions/{id}/switch` | 切换活跃会话 |

---

## 五、长期记忆系统

### 5.1 Milvus 记忆 Collection 设计

```python
collection_name = "user_memories"

schema = {
    "fields": [
        {"name": "id", "type": "INT64", "primary_key": True, "auto_id": True},
        {"name": "vector", "type": "FLOAT_VECTOR", "dim": 2048},
        {"name": "user_id", "type": "VARCHAR", "max_length": 64, "is_partition_key": True},
        {"name": "memory_type", "type": "VARCHAR", "max_length": 20},
        {"name": "content", "type": "VARCHAR", "max_length": 2000},
        {"name": "session_id", "type": "VARCHAR", "max_length": 64},
        {"name": "importance", "type": "FLOAT"},
        {"name": "created_at", "type": "INT64"},
    ]
}

index_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {"M": 16, "efConstruction": 256}
}
```

### 5.2 记忆类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **fact** | 事实性信息 | "用户是后端开发工程师" |
| **preference** | 用户偏好 | "用户喜欢简洁的回答" |
| **context** | 上下文知识 | "用户正在学习Python装饰器" |

### 5.3 记忆提取

```python
async def extract_memories(session_id: str, user_id: str,
                          user_message: str, ai_response: str):
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
"""

    result = await llm_complete(prompt, response_format="json")

    for memory in result.get("memories", []):
        await save_memory(user_id, memory, session_id)
```

### 5.4 记忆检索与注入

```python
async def retrieve_relevant_memories(user_id: str, query: str, top_k: int = 3):
    """检索与当前问题相关的记忆"""
    query_embedding = await embed_text(query)

    results = milvus.search(
        collection_name="user_memories",
        data=[query_embedding],
        limit=top_k,
        expr=f"user_id == '{user_id}' and importance > 0.5",
        output_fields=["content", "memory_type", "importance"]
    )

    return results[0] if results else []

def build_system_prompt(user_id: str, query: str) -> str:
    """构建包含记忆的系统提示"""

    base_prompt = """你是一个智能助手，根据用户的历史对话和知识库回答问题。"""

    # 1. 用户画像
    user_info = redis.hgetall(f"user:{user_id}")
    if user_info:
        base_prompt += f"\n\n【用户信息】\n昵称：{user_info.get('nickname', '用户')}"

    # 2. 相关记忆
    memories = await retrieve_relevant_memories(user_id, query)
    if memories:
        memory_text = "\n".join([f"- {m['content']}" for m in memories])
        base_prompt += f"\n\n【相关记忆】\n{memory_text}"

    return base_prompt
```

### 5.5 记忆管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/memories` | 获取用户所有记忆 |
| DELETE | `/api/v1/memories/{id}` | 删除指定记忆 |
| POST | `/api/v1/memories/compact` | 压重/清理冗余记忆 |

---

## 六、前端设计

### 6.1 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  Logo                  [搜索框]             [用户头像▼]      │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│ 会话列表  │              聊天内容区域                        │
│          │                                                  │
│ ━━━━━━  │                                                  │
│ 新建对话  │                                                  │
│ ━━━━━━  │                                                  │
│          │                                                  │
│ Python   │                                                  │
│ 装饰器   │                                                  │
│ RAG架构  │                                                  │
│          │                                                  │
├──────────┴──────────────────────────────────────────────────┤
│  📚 [技术文档 ×] [+ 添加 ▼]                                │
│  🌐 是否联网  │  [输入框...]                        [发送]  │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 用户状态管理

```javascript
const USER_STORAGE_KEY = 'rshanygen_user';

// 首次访问流程
1. 检查 LocalStorage 是否有 user_id
2. 调用 GET /api/v1/auth/me 验证
3. 如果无效，显示昵称输入弹窗
4. 提交昵称 → POST /api/v1/auth/register
5. 保存返回的 user_id 到 LocalStorage
```

### 6.3 会话管理组件

- **SessionList.jsx**: 左侧会话列表
- **SessionItem.jsx**: 单个会话项（可点击切换、右键删除）
- **NewSessionButton.jsx**: 新建会话按钮

---

## 七、配置文件

### 7.1 Redis 配置更新

```yaml
# config/default.yaml
dependencies:
  redis:
    host: "192.168.1.248"
    port: 6379
    db: 0
    ttl: 3600
    # 新增配置
    context:
      window_size: 10
      summary_threshold: 20
      summary_interval: 10
    memory:
      collection_name: "user_memories"
      embedding_model: "text-embedding-v3"
      retrieval_top_k: 3
      importance_threshold: 0.5
```

### 7.2 Admin 配置

```yaml
# config/default.yaml
admin:
  secret_phrase: "your_admin_secret"  # 暗语
  fixed_user_id: "admin-001"
```

---

## 八、实现要点

### 8.1 后端改动

**Gateway 层**:
- 新增 `apps/gateway/routers/auth.py` - 用户认证
- 新增 `apps/gateway/routers/sessions.py` - 会话管理
- 新增 `apps/gateway/routers/memories.py` - 记忆管理
- 更新 `apps/gateway/routers/chat.py` - 集成上下文构建

**Orchestrator 层**:
- 更新 `apps/orchestrator/graph/state.py` - 添加 user_id, session_id
- 新增 `apps/orchestrator/services/context_builder.py` - 上下文构建
- 新增 `apps/orchestrator/services/memory_extractor.py` - 记忆提取
- 新增 `apps/orchestrator/services/summary_generator.py` - 摘要生成

**依赖更新**:
- `redis` (异步客户端)
- `aioredis` 或 `redis-py` 的异步支持

### 8.2 前端改动

- 新增 `src/components/session/SessionList.jsx`
- 新增 `src/components/session/SessionItem.jsx`
- 新增 `src/components/auth/NicknameModal.jsx`
- 更新 `src/pages/ChatPage.jsx` - 集成会话列表
- 新增 `src/api/auth.js`
- 新增 `src/api/sessions.js`

### 8.3 数据库初始化

```python
# 创建 Milvus 记忆 Collection
from pymilvus import Collection, FieldSchema, CollectionSchema, DataType

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

schema = CollectionSchema(fields, description="User long-term memories")
collection = Collection(name="user_memories", schema=schema)

# 创建索引
index_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {"M": 16, "efConstruction": 256}
}
collection.create_index(field_name="vector", index_params=index_params)
```

---

## 九、后续扩展

- [ ] 记忆编辑功能（用户可手动修改记忆）
- [ ] 记忆分组（按主题/时间段）
- [ ] 记忆过期机制（旧记忆自动降权）
- [ ] 多语言记忆支持
- [ ] 记忆导出功能
- [ ] 会话分享功能
- [ ] 会话标签/分类
