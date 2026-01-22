# 多知识库功能设计文档

**日期**: 2025-01-21
**目标**: 实现多个独立知识库支持，用户可选择一个或多个知识库进行问答

---

## 一、需求概述

### 1.1 核心需求
- 支持创建多个独立的知识库，每个知识库由名称和自动生成的UUID标识
- 用户可以在聊天界面选择一个或多个知识库进行问答
- 未选择知识库时，系统使用纯聊天模式
- 管理员负责创建知识库，普通用户只能选择使用

### 1.2 环境信息
- **向量数据库**: Milvus @ 192.168.1.248:19530
- **业务数据库**: PostgreSQL @ 192.168.1.248:5432
- **管理界面**: PgAdmin @ http://192.168.1.248:5050
- **嵌入模型**: Zhipu embedding-3 (2048维)

---

## 二、架构设计

### 2.1 整体架构
采用**单Collection + Partition Key隔离**方案：
- 所有知识库共用一个Milvus Collection：`knowledge_bases`
- 使用 `kb_id` 作为Partition Key字段
- 检索时通过 `expr` 过滤指定的 `kb_id` 列表
- 多知识库检索采用**分别检索 + RRF融合**策略

### 2.2 数据流

**创建知识库：**
```
管理员创建 → 生成UUID(kb_*) → PostgreSQL创建记录 → Milvus自动创建分区
```

**上传文档：**
```
选择知识库 → 上传文件 → 文档绑定kb_id → 向量写入对应分区
```

**用户查询：**
```
选择KB列表 → 传入kb_ids → RAG服务检索 → RRF融合 → 返回结果
```

---

## 三、数据模型

### 3.1 PostgreSQL Schema

```sql
-- 知识库表
CREATE TABLE knowledge_bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_id TEXT UNIQUE NOT NULL,           -- 格式: kb_<uuid>
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    embedding_model TEXT DEFAULT 'zhipu',
    chunk_count INTEGER DEFAULT 0,
    doc_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'active'          -- active/deleted
);

CREATE INDEX idx_kb_status ON knowledge_bases(status) WHERE status = 'active';

-- 文档表
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    kb_id TEXT NOT NULL,
    name TEXT NOT NULL,
    size BIGINT,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'uploaded',       -- uploaded/processing/indexed/error
    chunks INTEGER DEFAULT 0,
    error_message TEXT,
    FOREIGN KEY (kb_id) REFERENCES knowledge_bases(kb_id) ON DELETE CASCADE
);

CREATE INDEX idx_docs_kb ON documents(kb_id);
CREATE INDEX idx_docs_status ON documents(status);
```

### 3.2 Milvus Collection Schema

```python
collection_name = "knowledge_bases"

schema = {
    "fields": [
        {"name": "id", "type": "INT64", "primary_key": True, "auto_id": False},
        {"name": "vector", "type": "FLOAT_VECTOR", "dim": 2048},
        {"name": "text", "type": "VARCHAR", "max_length": 65535},
        {"name": "kb_id", "type": "VARCHAR", "max_length": 64, "is_partition_key": True},
        {"name": "doc_id", "type": "VARCHAR", "max_length": 64},
        {"name": "chunk_index", "type": "INT64"},
        {"name": "chunk_type", "type": "VARCHAR", "max_length": 20},
    ]
}

index_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {"M": 16, "efConstruction": 256}
}
```

---

## 四、API接口设计

### 4.1 知识库管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/kb` | 列出所有知识库 |
| POST | `/api/v1/kb` | 创建知识库 |
| GET | `/api/v1/kb/{kb_id}` | 获取知识库详情 |
| PUT | `/api/v1/kb/{kb_id}` | 更新知识库 |
| DELETE | `/api/v1/kb/{kb_id}` | 删除知识库（级联删除文档和向量） |

### 4.2 文档管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/kb/{kb_id}/documents` | 列出知识库下的文档 |
| POST | `/api/v1/kb/{kb_id}/documents` | 上传文档到指定知识库 |
| POST | `/api/v1/kb/{kb_id}/documents/{doc_id}/index` | 索引文档 |
| DELETE | `/api/v1/documents/{doc_id}` | 删除文档 |

### 4.3 检索接口

```python
POST /api/v1/search

# 请求体
{
    "query": "用户问题",
    "kb_ids": ["kb_xxx", "kb_yyy"],  # 知识库ID列表
    "top_k": 5,
    "rerank": true
}

# 多KB检索逻辑
1. 为每个kb_id分别检索top_k结果
2. 使用RRF融合所有结果
3. 返回融合后的top_k结果
```

---

## 五、UI/UX设计

### 5.1 聊天页面布局

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  聊天内容区域...                                              │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  📚 [默认知识库 ×] [技术文档 ×] [选择知识库 ▼]                │  ← 知识库选择器
│                                                             │
│  🌐 是否联网  │  [输入框...]                        [发送]  │  ← 现有输入框
└─────────────────────────────────────────────────────────────┘
```

### 5.2 交互行为

| 场景 | 显示 |
|------|------|
| 未选择 | `📚 选择知识库 ▼`（空状态，渐变背景） |
| 已选择1个 | `📚 [知识库名 ×] [+ 添加 ▼]` |
| 已选择多个 | `📚 [KB1 ×] [KB2 ×] [KB3 ×] [+ 添加 ▼]` |

### 5.3 空状态样式

```css
.kb-select-empty {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border: 1px solid #cbd5e1;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.kb-select-empty:hover {
  background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
```

---

## 六、路由逻辑

### 6.1 简化后的图流程

```
user_message → [判断kb_ids]
                    ├─ 有kb_ids → rag_retriever → llm_generator
                    └─ 无kb_ids → llm_generator
```

### 6.2 路由函数

```python
# apps/orchestrator/graph/agent_graph.py

def route_after_intent(state):
    kb_ids = state.get("kb_ids", [])

    if kb_ids:
        return "rag_retriever"  # 查询选中的知识库
    return "llm_generator"      # 纯聊天模式
```

### 6.3 前端传参

```jsx
await send(message, {
  kbIds: selectedKbIds.map(kb => kb.id),  // ['kb_xxx', 'kb_yyy']
  onChunk: (content) => {...}
});
```

---

## 七、实现要点

### 7.1 RAG服务改造

**向量存储层 (`vector_store.py`)**
- 支持创建带Partition Key的Collection
- 插入时携带 `kb_id` 字段
- 检索时使用 `expr=f"kb_id in {kb_ids}"` 过滤

**检索层 (`retriever.py`)**
- 接收 `kb_ids` 参数
- 多KB时分别检索并RRF融合

### 7.2 前端改造

**新增组件**
- `KbSelector.jsx` - 知识库选择器
- `KbTag.jsx` - 知识库标签组件

**API调用**
- `GET /api/v1/kb` - 获取知识库列表
- 传递 `kbIds` 到聊天接口

### 7.3 数据库迁移

- 创建PostgreSQL表结构
- 删除旧的SQLite数据库（不需要迁移测试数据）
- 初始化Milvus Collection

---

## 八、配置文件

### 8.1 PostgreSQL配置

```yaml
# config/database.yaml
postgresql:
  host: 192.168.1.248
  port: 5432
  database: rshanygen
  user: postgres
  password: your_password
  pool_size: 10
```

### 8.2 Milvus配置

```yaml
# config/vector_db.yaml
milvus:
  host: 192.168.1.248
  port: 19530
  timeout: 60
  collection_name: knowledge_bases
  partition_key: kb_id
```

---

## 九、后续扩展

- [ ] 知识库权限管理（用户只能访问特定KB）
- [ ] 知识库统计（文档数、chunk数、查询热度）
- [ ] 知识库导出/导入
- [ ] 联网搜索功能（与KB并行）
