# rshAnyGen 开源 Agent 系统 - 设计方案

> **项目目标**：构建一个模块化的、支持 MCP/Skills/联网搜索的中文 Agent 系统，使用在线 LLM API，开源 UI，最优 RAG 能力

**设计日期**：2025-01-16

---

## 目录

1. [系统概览](#一系统概览)
2. [配置系统设计](#二配置系统设计)
3. [核心组件设计](#三核心组件设计)
4. [API 网关设计](#四api-网关设计)
5. [Agent 编排层设计](#五agent-编排层设计)
6. [MCP 管理器设计](#六mcp-管理器设计)
7. [Skills Registry 设计](#七skills-registry-设计)
8. [RAG Pipeline 设计](#八rag-pipeline-设计)
9. [前端 UI 设计](#九前端-ui-设计)
10. [部署配置与开发脚本](#十部署配置与开发脚本)
11. [依赖包管理](#十一依赖包管理)

---

## 一、系统概览

### 核心决策

| 决策项 | 选择 | 说明 |
|--------|------|------|
| MVP 策略 | 全栈 MVP | 一次性实现所有组件的简化版本 |
| LLM API | 多提供商支持 | 通义千问、智谱 AI、Kimi、OpenAI，可配置切换 |
| 向量数据库 | 多数据库支持 | Milvus、Qdrant、PGVector，可配置切换 |
| 嵌入/重排 API | 多提供商支持 | Cohere、Jina、国内服务商（通义、智谱） |
| 目录结构 | 按文档结构 | 遵循架构文档的组织方式 |
| 开发环境 | 本地 + Docker + K8s | 支持本地开发、Docker 部署、K8s 集群 |
| 前端方案 | Fork Open WebUI | 在 Open WebUI 基础上二次开发 |
| 测试框架 | pytest + E2E | 单元测试 + E2E 测试 |

### 服务端口分配

使用 **9300+** 端口段（避免冲突）：

| 服务 | 端口 | 说明 |
|------|------|------|
| Web UI | 9300 | 前端界面 |
| Gateway | 9301 | API 网关 |
| Orchestrator | 9302 | Agent 编排器 |
| Skills Registry | 9303 | Skills 注册中心 |
| MCP Manager | 9304 | MCP 管理服务 |
| RAG Pipeline | 9305 | RAG 管线服务 |

### 项目目录结构

```
rshAnyGen/
├── apps/
│   ├── shared/              # 共享模块
│   │   ├── config_loader.py
│   │   ├── logger.py
│   │   └── tests/
│   ├── web-ui/              # Open WebUI fork
│   ├── gateway/             # FastAPI 网关
│   └── orchestrator/        # LangGraph 编排器
├── services/
│   ├── mcp-baidu-search/
│   ├── mcp-knowledge/
│   ├── mcp-manager/
│   ├── skills-registry/
│   └── rag-pipeline/
├── config/                  # 配置文件目录
│   ├── default.yaml         # 默认配置
│   ├── llm.yaml
│   ├── vector_db.yaml
│   ├── embedding.yaml
│   ├── mcp.yaml
│   ├── skills.yaml
│   └── rag.yaml
├── scripts/
│   ├── dev.sh               # 一键启动
│   ├── install.sh           # 安装依赖
│   └── test.sh              # 测试运行
├── logs/                    # 日志目录
│   ├── gateway/
│   ├── orchestrator/
│   ├── mcp/
│   ├── skills/
│   └── rag/
├── tests/                   # 统一测试目录
│   ├── unit/                # 按模块分
│   ├── integration/
│   ├── e2e/
│   ├── fixtures/
│   ├── conftest.py
│   └── pytest.ini
├── deploy/
│   ├── docker/
│   └── k8s/
└── docs/
```

---

## 二、配置系统设计

### 配置文件结构

**config/default.yaml** - 默认配置（包含所有默认值）
**config/llm.yaml** - LLM API 配置
**config/vector_db.yaml** - 向量数据库配置
**config/embedding.yaml** - 嵌入/重排配置
**config/mcp.yaml** - MCP 服务配置
**config/skills.yaml** - Skills 配置
**config/rag.yaml** - RAG 管线配置

### 配置加载器

支持：
- YAML 配置文件
- 环境变量替换 `${VAR_NAME}`
- 默认值 `${VAR_NAME:-default}`
- 点分隔路径访问 `llm.providers.qwen.api_key`

---

## 三、核心组件设计

### 统一日志管理器

- 按服务分类存储日志
- 日志文件按日期滚动
- 控制台 + 文件双输出
- 统一日志格式

### 统一配置加载器

- 默认配置 + 环境变量覆盖
- YAML 文件解析
- 点分隔路径访问

---

## 四、API 网关设计

### 核心接口

1. **POST /api/v1/chat/stream** - 流式聊天接口（SSE）
2. **GET /api/v1/skills** - 获取 Skills 列表
3. **POST /api/v1/skills/{id}/toggle** - 启用/禁用 Skill

### 中间件

- 会话管理中间件（Redis）
- 速率限制中间件
- 权限控制中间件

---

## 五、Agent 编排层设计

### LangGraph 状态定义

```python
class AgentState(TypedDict):
    session_id: str
    user_message: str
    chat_history: List[dict]
    intent: str  # "search" | "knowledge" | "chat"
    selected_skill: Optional[str]
    tool_call_approved: bool
    retrieved_docs: List[dict]
    final_answer: str
    citations: List[dict]
```

### 编排流程

```
意图识别 → 路由决策 → [搜索分支 / RAG 分支 / 直接对话]
           ↓
        LLM 生成 → 返回结果
```

---

## 六、MCP 管理器设计

### 支持的传输类型

- **stdio** - 本地进程通信（百度搜索、知识库）
- **HTTP** - REST API（远程服务）
- **SSE** - Server-Sent Events（实时流式）

### MCP 配置

```yaml
servers:
  baidu-search:
    transport: "stdio"
    command: "python"
    args: ["-m", "mcp_baidu_search.server"]

  remote-rag:
    transport: "http"
    url: "http://localhost:9306/mcp"

  stream-tools:
    transport: "sse"
    url: "http://localhost:9307/sse"
```

---

## 七、Skills Registry 设计

### 遵循 Claude Skills 官方规范

**Skill 文件结构：**
```
skills/
└── web-search/
    ├── SKILL.md          # 技能描述
    └── api.py            # API 实现
```

**SKILL.md 格式：**
```markdown
---
name: web_search
title: Web Search
category: search
version: 1.0.0
---

# Web Search

Search the web for current information.

## Use when
- User asks for current events
- User needs to verify facts

## Parameters
- `query` (string, required): The search query
```

---

## 八、RAG Pipeline 设计

### 支持的文档格式

| 格式 | 说明 |
|------|------|
| TXT | 纯文本 |
| MD | Markdown |
| PDF | 支持 OCR（扫描版） |
| 图片 | JPG/PNG/BMP（OCR 识别） |
| Word | .docx, .doc（LibreOffice 转换） |
| Excel | .xlsx, .xls |
| PowerPoint | .pptx, .ppt |
| CSV | 用 Excel 加载器 |
| HTML | 网页加载 |

### RAG 流程

```
文档入库：加载 → 分块(Parent-Child) → 嵌入 → 索引

查询流程：查询嵌入 → 向量检索 → BM25检索 → RRF融合 → Rerank → Top 5
```

---

## 九、前端 UI 设计

### 基于 Open WebUI 定制

- Fork Open WebUI 进行二次开发
- 使用 **ui-ux-pro-max** 技能优化 UI 风格

### 品牌色彩（新能源集团）

```css
--brand-gradient: linear-gradient(135deg, #0066CC 0%, #00B388 100%);
--brand-primary: #0088AA;
```

### 设计风格

- **Swiss Modernism 2.0** - 网格系统、模块化
- **Minimalism** - 高对比度、清晰层次

### 字体

```css
font-family-heading: 'Lexend', sans-serif;
font-family-body: 'Source Sans 3', sans-serif;
```

---

## 十、部署配置与开发脚本

### Docker 支持

**deploy/docker/docker-compose.yml**
- Redis
- Milvus（含 etcd、minio）
- Gateway
- Orchestrator
- Skills Registry
- Web UI

### Kubernetes 支持

**deploy/k8s/**
- namespace.yaml
- configmap.yaml
- gateway-deployment.yaml
- orchestrator-deployment.yaml
- services/

### 开发脚本

| 脚本 | 功能 |
|------|------|
| scripts/dev.sh | 一键启动开发环境 |
| scripts/stop.sh | 停止所有服务 |
| scripts/install.sh | 安装所有依赖 |
| scripts/test.sh | 运行测试（支持模块选择） |

---

## 十一、依赖包管理

### 共享依赖

**requirements-shared.txt**
- FastAPI
- Redis / Milvus / Qdrant 客户端
- pytest 测试框架

### 各服务依赖

- Gateway: FastAPI + 限流 + 认证
- Orchestrator: LangGraph + LangChain
- RAG: 文档加载器 + OCR + 分词
- Web UI: Vue3 + Vite + Tailwind

---

## 附录：测试策略

### 测试目录结构

```
tests/
├── unit/                    # 按模块分
│   ├── shared/
│   ├── gateway/
│   ├── orchestrator/
│   ├── mcp/
│   ├── skills/
│   └── rag/
├── integration/
│   ├── agent/
│   └── rag/
├── e2e/
│   ├── chat/
│   └── search/
├── fixtures/
├── conftest.py
└── pytest.ini
```

### TDD 原则

1. 每个功能完成后立即编写单元测试
2. 测试通过后再做下一个功能
3. 每个模块可独立测试

---

*设计方案完成日期：2025-01-16*
