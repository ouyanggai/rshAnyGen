## 优先级
- 先做：Keycloak 认证（前端登录 + 后端强制鉴权）→ 真实用户管理（Keycloak Users/Roles）→ 对话会话化与上下文接入
- 后做：MaxKey

## 第 1 部分：Keycloak 认证（端到端闭环）
1. 统一 Keycloak 配置来源（避免 issuer/realm/client 漂移），并以 `/auth/config` 作为前端初始化入口。
2. Web UI 接入 OIDC 授权码 + PKCE（keycloak-js / React Provider），实现：登录、登出、token 刷新、axios 自动注入 Bearer。
3. 网关落地强制鉴权策略：明确免鉴权白名单（/health、/auth/*），其余关键路由使用 `require_auth`/RBAC 依赖。
4. 前端路由守卫：未登录不能进入聊天与 admin；admin 页面基于角色控制。

## 第 2 部分：真实用户管理（Keycloak Admin API）
1. 在后端封装 Keycloak Admin Client（用 backend-api confidential client 获取管理 token）。
2. 新增 admin-only 用户管理接口：用户列表/创建/禁用/重置密码/角色分配。
3. Web UI 新增“用户管理”页：列表 + 创建/禁用/重置密码 + 角色分配（最小可用）。

## 第 3 部分：对话改进（按计划 Task 4–6 的“集成”缺口补齐）
1. Gateway 新增 SessionService/MessageService（Redis）：会话创建/列表/切换，消息写入与读取，按 token 裁剪。
2. chat/stream 接入 ContextBuilder：构建上下文→转发给 Orchestrator→流式结束后落库消息。
3. Orchestrator prompt 改造：把 `chat_history` 真正进入 LLM 输入（history + 当前消息 + retrieved docs）。
4. Web UI HistoryPage 从后端读取会话与消息，替代 localStorage demo。

## 验证（每阶段都做）
- 认证：无 token 访问受保护接口 401；非 admin 调用用户管理 403；token 过期可刷新。
- 用户管理：创建用户→登录→userinfo；禁用后访问受限。
- 对话：同会话多轮上下文生效；不同会话/不同用户完全隔离。

确认后我将立即开始第 1 部分（Keycloak 前端登录 + 后端强制鉴权）并逐步推进后续两部分。