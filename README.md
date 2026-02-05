# rshAnyGen - 企业级 AI 智能体平台

rshAnyGen 是一个现代化的企业级 AI Agent 平台，集成了多模型编排、RAG 知识库检索、MCP 工具协议以及动态技能扩展能力。旨在为企业提供安全、高效、可扩展的 AI 应用构建方案。

## 核心特性

- **多模型支持**: 通过统一网关（Gateway）和编排器（Orchestrator）支持多种 LLM 模型接入。
- **RAG 知识库**: 内置强大的 RAG 流水线，支持 PDF、Word、Excel、TXT 等多种格式文档的解析与检索。
- **MCP 协议集成**: 支持 Model Context Protocol (MCP)，实现标准化的工具调用与上下文增强。
- **动态技能注册**: 提供 Skills Registry 服务，支持从 Git 仓库动态加载和执行 Python/JavaScript 技能。
- **现代化 Web UI**: 基于 React + Tailwind CSS 构建的专业级用户界面，提供流畅的对话体验与管理功能。
- **企业级安全**: 集成 Casdoor/Keycloak 认证体系，支持单点登录（SSO）与细粒度权限控制。
- **长期记忆**: 具备多轮对话上下文管理与长期记忆存储能力。

## 系统架构

项目采用微服务架构设计，主要包含以下核心组件：

- **Gateway (端口 9301)**: 统一 API 网关，处理鉴权、路由与协议转换。
- **Orchestrator (端口 9302)**: 智能编排核心，负责意图识别、任务拆解与结果合成。
- **Skills Registry (端口 9303)**: 技能注册中心，管理工具与扩展能力的生命周期。
- **Web UI (端口 9300)**: 前端交互界面，提供对话、知识库管理、技能配置等功能。
- **RAG Pipeline (端口 9305)**: 独立的文档处理与向量检索服务。

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Redis & Qdrant (向量数据库)

### 开发环境启动

1. **启动基础服务**
   ```bash
   # 启动 Redis, Qdrant, Postgres 等依赖
   docker-compose up -d
   ```

2. **启动后端服务**
   ```bash
   ./scripts/dev.sh
   ```

3. **启动前端**
   ```bash
   cd apps/web-ui
   npm install
   npm run dev
   ```

## 文档资源

- [常用命令 (COMMANDS.md)](./COMMANDS.md)
- [Agent 设计文档 (AGENT.md)](./AGENT.md)
- [测试指南 (TESTING.md)](./TESTING.md)

## 许可证

MIT License
