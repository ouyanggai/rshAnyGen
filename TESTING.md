# Phase 9: 系统测试指南

## 快速开始

### 1. 获取 API Key

**推荐方案（按优先级）：**

#### 方案 A: 智谱 AI（免费，推荐测试）
```bash
# 访问: https://open.bigmodel.cn
# 注册后获取 API Key
export ZHIPU_LLM_API_KEY="your_key_here"
```

#### 方案 B: DeepSeek（最便宜）
```bash
# 访问: https://platform.deepseek.com
# 注册后充值（建议先充值 1 元测试）
export DEEPSEEK_API_KEY="your_key_here"
```

#### 方案 C: 通义千问（阿里云）
```bash
# 访问: https://dashscope.aliyun.com
# 注册后获取 API Key
export QWEN_LLM_API_KEY="your_key_here"
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# 只需配置一个 LLM API 即可
```

### 3. 启动服务

```bash
# Terminal 1: 启动 Gateway
cd /path/to/rshAnyGen
python -m apps.gateway.main

# Terminal 2: 启动 Orchestrator
python -m apps.orchestrator.main

# Terminal 3: 启动 Web UI
cd apps/web-ui
npm run dev
```

### 4. 访问界面

打开浏览器访问: http://localhost:5173

---

## 测试流程

### 测试 1: 基础对话测试

```bash
# 使用 curl 测试 Gateway
curl -X POST http://localhost:9301/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-001",
    "message": "你好，请介绍一下你自己"
  }'
```

### 测试 2: 流式输出测试

```bash
# 测试 SSE 流式响应
curl -N http://localhost:9301/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-002", 
    "message": "写一首关于人工智能的诗"
  }'
```

### 测试 3: RAG 检索测试

```bash
# 测试文档检索
curl -X POST http://localhost:9301/api/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是 rshAnyGen？",
    "top_k": 3
  }'
```

### 测试 4: Skills 调用测试

```bash
# 测试 Skill 执行
curl -X POST http://localhost:9301/api/skills/execute \
  -H "Content-Type: application/json" \
  -d '{
    "skill_name": "web_search",
    "params": {
      "query": "人工智能最新进展"
    }
  }'
```

---

## 常见问题

### Q1: API Key 无效
```
Error: 401 Unauthorized
```
**解决:** 检查 API Key 是否正确配置，确保没有多余空格

### Q2: 服务启动失败
```
Error: Port 9301 already in use
```
**解决:** 
```bash
# 查找占用端口的进程
lsof -i :9301
# 杀死进程
kill -9 <PID>
```

### Q3: 前端无法连接后端
```
Error: connect ECONNREFUSED
```
**解决:** 确保后端服务已启动，检查端口是否正确

### Q4: LLM 响应很慢
**解决:** 
- 尝试切换到更快的模型 (如 glm-4-flash, qwen-turbo)
- 检查网络连接
- 使用国内 API 提供商

---

## 性能基准

| 指标 | 目标值 |
|------|--------|
| 首字响应时间 | < 2秒 |
| 流式输出延迟 | < 500ms/token |
| RAG 检索时间 | < 1秒 |
| 并发会话支持 | > 100 |

---

## API Key 平台对比

| 平台 | 免费额度 | 价格 | 速度 | 推荐场景 |
|------|---------|------|------|----------|
| 智谱 AI | ✓ 有 | ¥0.1/千tokens | 快 | 测试、开发 |
| DeepSeek | ✗ 无 | ¥0.001/千tokens | 快 | 生产环境 |
| 通义千问 | ✓ 有 | ¥0.5/百万tokens | 快 | 中文场景 |
| OpenAI | ✗ 无 | $0.15/百万tokens | 慢 | 海外用户 |

---

## 下一步

测试通过后，可以：
1. 修改 `apps/web-ui/src/hooks.server.ts` 调整 API 代理
2. 添加自定义 Skills 到 `services/skills_registry/`
3. 配置自己的知识库到 RAG Pipeline
4. 部署到生产环境 (参考 `deploy/` 目录)
