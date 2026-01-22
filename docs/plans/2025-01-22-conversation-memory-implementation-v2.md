# 多轮对话与长期记忆系统实施计划 (优化版 v2)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标**: 实现基于主流方案的多轮对话、长期记忆和统一认证系统
**技术栈**: Redis, Milvus, Keycloak/MaxKey, FastAPI, React
**时间**: 6周

**优化说明**: 本计划基于评审文档进行了全面优化，主要改进包括：
- Token-aware 三级上下文管理
- 主题感知智能摘要生成
- 三层记忆架构（用户画像+实体记忆+语义记忆）
- Keycloak/MaxKey OIDC 统一认证（对比选型中）
- 记忆去重与时间衰减机制

**进度概览**: 2025-01-22 更新

| Phase | 状态 | 说明 |
|-------|------|------|
| Phase 1: 认证系统部署 | ✅ 完成 | Keycloak 和 MaxKey 已部署，对比选型中 |
| Phase 2: Token-aware 上下文 | 🟡 进行中 | Token 计数器和上下文构建器已创建 |
| Phase 3-6: 待实施 | ⏳ 待开始 | 智能摘要、实体记忆、语义记忆优化 |

---

## 服务器基础设施

### 服务器信息

| 属性 | 值 |
|------|-----|
| **IP 地址** | 192.168.1.248 |
| **SSH 用户** | root | 密码 524478201
| **部署目录** | /root/keycloak, /root/maxkey |
| **操作系统** | Ubuntu 22.04.5 LTS |

### 服务端口分配

| 服务 | 端口 | URL | 状态 |
|------|------|-----|------|
| **Keycloak** | 8080 | http://192.168.1.248:8080 | ✅ 运行中 |
| **Keycloak Admin** | 8080 | http://192.168.1.248:8080/admin | ✅ 可访问 |
| **MaxKey 认证前端** | 8527 | http://192.168.1.248:8527 | 🟡 部署中 |
| **MaxKey 管理前端** | 8526 | http://192.168.1.248:8526 | 🟡 部署中 |
| **MaxKey 认证后端** | 9527 | http://192.168.1.248:9527 | 🟡 配置中 |
| **MaxKey 管理后端** | 9526 | http://192.168.1.248:9526 | 🟡 配置中 |
| **PostgreSQL** | 5432 | 内部 | ✅ 运行中 |
| **MySQL** | 3307 | 内部 | 🟡 配置中 |
| **Redis** | 6379 | 192.168.1.248:6379 | ✅ 可用 |

### Docker 容器状态

```bash
# Keycloak 容器
keycloak          (quay.io/keycloak/keycloak:23.0)    ✅ Running
keycloak-db       (postgres:15-alpine)                 ✅ Running

# MaxKey 容器
maxkey            (maxkeytop/maxkey:latest)            🟡 Restarting
maxkey-mgt        (maxkeytop/maxkey-mgt:latest)        🟡 Restarting
maxkey-frontend   (maxkeytop/maxkey-frontend:latest)   ✅ Running
maxkey-mgt-frontend (maxkeytop/maxkey-mgt-frontend:latest) ✅ Running
maxkey-db         (mysql:8.0.27)                       🟡 Restarting
```

---

## 认证系统对比 (Keycloak vs MaxKey)

### 部署状态对比

| 特性 | Keycloak | MaxKey |
|------|----------|--------|
| **部署状态** | ✅ 完全运行 | 🟡 配置中 |
| **数据库** | PostgreSQL | MySQL |
| **管理后台** | http://192.168.1.248:8080/admin | http://192.168.1.248:8526 |
| **管理账号** | admin / admin_password | 首次初始化设置 |
| **Realm/App** | rshAnyGen | 默认应用 |
| **中文支持** | 英文为主 | ✅ 国产中文 |
| **文档** | 英文 | ✅ 中文 |
| **社区** | 国际活跃 | 国内活跃 |

### 技术对比

| 项目 | Keycloak | MaxKey |
|------|----------|--------|
| **开源协议** | Apache 2.0 | Apache 2.0 |
| **开发商** | Red Hat | Dromara (国产) |
| **协议支持** | OAuth 2.0, OIDC, SAML | OAuth 2.0, OIDC, SAML, CAS |
| **界面语言** | 英文 | 中文 |
| **学习曲线** | 中等 | 较低 |
| **企业功能** | 全面 | 全面 |

### 当前建议

**推荐使用 Keycloak** - 原因：
1. 部署稳定，已完全配置完成
2. 国际成熟方案，社区活跃
3. 后端集成已完成（JWT 中间件、认证路由）
4. 文档完善，易于扩展

**MaxKey 作为备选** - 优势：
1. 国产方案，中文文档友好
2. 支持 CAS 协议（如需兼容旧系统）
3. 界面本地化更好

---

## Phase 1: 统一认证系统 ✅ 已完成

### Task 1: 部署 Keycloak ✅

**完成时间**: 2025-01-22

**部署位置**: `192.168.1.248:8080`

**配置文件**:
- `docker-compose.keycloak.yml` - Docker Compose 配置
- `docs/keycloak-config.md` - 详细配置文档

**Realm 和 Clients 配置完成**:
- Realm `rshAnyGen` ✅
- Client `web-ui` (public) ✅
- Client `backend-api` (confidential) ✅

**访问信息**:
```
Keycloak URL: http://192.168.1.248:8080
管理控制台: http://192.168.1.248:8080/admin
Realm: rshAnyGen
Admin 用户名: admin
Admin 密码: admin_password

前端 Client: web-ui (public, 用于 OIDC 登录)
后端 Client: backend-api
Client Secret: backend-secret-123456
```

**API 端点**:
- Token 端点: `http://192.168.1.248:8080/realms/rshAnyGen/protocol/openid-connect/token`
- JWKS 端点: `http://192.168.1.248:8080/realms/rshAnyGen/protocol/openid-connect/certs`
- 用户信息端点: `http://192.168.1.248:8080/realms/rshAnyGen/protocol/openid-connect/userinfo`

---

### Task 2: 后端集成 Keycloak JWT 验证 ✅

**完成时间**: 2025-01-22

**已创建文件**:
- `apps/gateway/middleware/auth.py` - JWT 认证中间件，包含 JWKS 缓存和 token 验证
- `apps/gateway/routers/auth.py` - 认证路由，包含登录/登出/token交换等接口
- `apps/gateway/config.py` - Keycloak 配置
- `config/default.yaml` - 共享 Keycloak 配置

**功能实现**:
- ✅ JWT Token 验证 (RS256)
- ✅ JWKS 公钥缓存 (自动刷新)
- ✅ 认证中间件 (可选路径跳过)
- ✅ 认证路由 (登录、登出、token 交换、用户信息)
- ✅ 配置文件集成

**依赖**:
- `python-jose[cryptography]>=3.3.0` - 已在 gateway/requirements.txt

---

### Task 3: 前端集成 Keycloak ⏳ 待实施

**计划中的前端集成** (未完成):
- 安装 `@react-keycloak/web` 和 `keycloak-js`
- 创建 Keycloak 配置和 Provider
- 创建登录/登出组件
- 集成到 ChatPage

**说明**: 前端集成可以后续进行，当前后端 API 已完全可用

---

## Phase 2: Token-aware 上下文管理 🟡 进行中

### Task 4: 实现 Token 计数器 ✅

**完成时间**: 2025-01-22

**已创建文件**:
- `apps/shared/token_counter.py` - Token 计数器，支持 tiktoken

**功能实现**:
- ✅ 文本 token 计数
- ✅ 消息 token 计数
- ✅ 消息列表裁剪 (按 token 限制)
- ✅ 模型编码器映射 (qwen-max, gpt-4 等)

**依赖**:
- `tiktoken>=0.5.0` - 已添加到 orchestrator/requirements.txt

---

### Task 5: 实现三级上下文构建器 ✅

**完成时间**: 2025-01-22

**已创建文件**:
- `apps/gateway/services/context_builder.py` - 三级上下文构建器
- `apps/shared/redis_client.py` - Redis 操作封装 (JSON 支持)
- `apps/gateway/services/__init__.py`
- `config/default.yaml` - 添加 context 配置

**功能实现**:
- ✅ 长期记忆层 (用户画像 - Redis)
- ✅ 短期摘要层 (会话摘要 - Redis)
- ✅ 工作记忆层 (最近消息 - Token 裁剪)
- ✅ 上下文配置 (working_memory max_tokens: 2048)

**上下文预算分配**:
```
- 长期记忆: ~200 tokens
- 短期摘要: ~500 tokens
- 工作记忆: ~2048 tokens
- 当前消息: ~100 tokens
总计: ~2848 tokens
```

---

### Task 6: 集成上下文构建到聊天流程 ⏳ 部分完成

**进度**: 基础架构已创建，待集成到实际聊天流程

**已创建**:
- `apps/gateway/models.py` - ChatRequest 添加 model 字段
- `apps/gateway/services/context_builder.py` - 上下文构建器

**待完成**:
- 在 `apps/gateway/routers/chat.py` 中集成 ContextBuilder
- 实现消息保存到 Redis
- 实现 Session 服务 (创建/获取/设置活跃会话)

### Task 1: 部署 Keycloak

**Files:**
- Create: `docker-compose.keycloak.yml`
- Create: `scripts/init_keycloak.sh`

**Step 1: 创建 Docker Compose 配置**

```yaml
# docker-compose.keycloak.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: keycloak-db
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: keycloak_password
    volumes:
      - keycloak-db:/var/lib/postgresql/data
    networks:
      - keycloak-net

  keycloak:
    image: quay.io/keycloak/keycloak:23.0
    container_name: keycloak
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: keycloak_password
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin_password
      KC_HOSTNAME: 192.168.1.248
      KC_HTTP_ENABLED: true
      KC_PROXY: edge
    ports:
      - "8080:8080"
    depends_on:
      - postgres
    command: start-dev
    networks:
      - keycloak-net

networks:
  keycloak-net:
    driver: bridge

volumes:
  keycloak-db:
```

**Step 2: 创建初始化脚本**

```bash
# scripts/init_keycloak.sh
#!/bin/bash

echo "正在启动 Keycloak..."
docker-compose -f docker-compose.keycloak.yml up -d

echo "等待 Keycloak 启动(约60秒)..."
sleep 60

echo "Keycloak 管理控制台: http://192.168.1.248:8080/admin"
echo "用户名: admin"
echo "密码: admin_password"
echo ""
echo "请手动完成以下配置:"
echo "1. 创建 Realm: rshAnyGen"
echo "2. 创建 Client: web-ui (Public, 启用 Standard Flow)"
echo "3. 创建 Client: backend-api (Confidential, 启用 Service Account)"
echo "4. 配置 Valid Redirect URIs: http://localhost:9300/*"
echo "5. 配置 Web Origins: http://localhost:9300"
```

**Step 3: 启动并验证**

Run: `chmod +x scripts/init_keycloak.sh && ./scripts/init_keycloak.sh`

Expected:
- 访问 http://192.168.1.248:8080/admin
- 成功登录管理控制台

**Step 4: 手动配置 Keycloak**

1. 创建 Realm `rshAnyGen`
2. 创建 Client `web-ui`:
   - Client Protocol: openid-connect
   - Access Type: public
   - Valid Redirect URIs: `http://localhost:9300/*`
   - Web Origins: `http://localhost:9300`
3. 创建 Client `backend-api`:
   - Access Type: confidential
   - Service Accounts Enabled: ON
4. 创建测试用户: `test@example.com` / `password123`

**Step 5: Commit**

```bash
git add docker-compose.keycloak.yml scripts/init_keycloak.sh
git commit -m "feat: add keycloak deployment config"
```

---

### Task 2: 后端集成 Keycloak JWT 验证

**Files:**
- Create: `apps/gateway/middleware/auth.py`
- Modify: `apps/gateway/requirements.txt`
- Modify: `apps/gateway/main.py`
- Update: `config/default.yaml`

**Step 1: 添加依赖**

```bash
echo "python-jose[cryptography]==3.3.0" >> apps/gateway/requirements.txt
echo "python-keycloak==3.8.0" >> apps/gateway/requirements.txt
pip install -r apps/gateway/requirements.txt
```

**Step 2: 创建 JWT 验证中间件**

```python
# apps/gateway/middleware/auth.py
"""Keycloak JWT 认证中间件"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional
import httpx

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("auth_middleware")
logger = logger_manager.get_logger()

# Keycloak 配置
KEYCLOAK_URL = config.get("keycloak.url", "http://192.168.1.248:8080")
REALM = config.get("keycloak.realm", "rshAnyGen")
CLIENT_ID = config.get("keycloak.client_id", "backend-api")

# JWT 配置
ALGORITHM = "RS256"
PUBLIC_KEY_CACHE = None

security = HTTPBearer()


async def get_keycloak_public_key() -> str:
    """获取 Keycloak 公钥"""
    global PUBLIC_KEY_CACHE

    if PUBLIC_KEY_CACHE:
        return PUBLIC_KEY_CACHE

    # 从 Keycloak 获取公钥
    url = f"{KEYCLOAK_URL}/realms/{REALM}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        public_key = f"-----BEGIN PUBLIC KEY-----\n{data['public_key']}\n-----END PUBLIC KEY-----"
        PUBLIC_KEY_CACHE = public_key
        return public_key


async def verify_token(token: str) -> dict:
    """验证 JWT Token"""
    try:
        public_key = await get_keycloak_public_key()

        # 验证并解码 Token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[ALGORITHM],
            audience=CLIENT_ID
        )

        return payload

    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = security
) -> dict:
    """从 Token 获取当前用户信息"""
    token = credentials.credentials
    payload = await verify_token(token)

    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "preferred_username": payload.get("preferred_username"),
        "roles": payload.get("realm_access", {}).get("roles", [])
    }


class AuthMiddleware:
    """认证中间件"""

    # 无需认证的路径
    EXCLUDED_PATHS = [
        "/docs",
        "/openapi.json",
        "/health"
    ]

    async def __call__(self, request: Request, call_next):
        # 检查是否需要认证
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        # 获取 Token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token"
            )

        token = auth_header.split(" ")[1]

        try:
            # 验证 Token
            payload = await verify_token(token)

            # 将用户信息注入 request.state
            request.state.user_id = payload.get("sub")
            request.state.email = payload.get("email")
            request.state.username = payload.get("preferred_username")

            logger.info(f"Authenticated user: {request.state.user_id}")

        except HTTPException:
            raise

        return await call_next(request)
```

**Step 3: 注册中间件**

```python
# apps/gateway/main.py
from apps.gateway.middleware.auth import AuthMiddleware

# 注册中间件
app.middleware("http")(AuthMiddleware())
```

**Step 4: 更新配置**

```yaml
# config/default.yaml
# 在文件末尾添加
keycloak:
  url: "http://192.168.1.248:8080"
  realm: "rshAnyGen"
  client_id: "backend-api"
  client_secret: "YOUR_CLIENT_SECRET"  # 从 Keycloak 获取
```

**Step 5: 创建测试**

```python
# tests/gateway/middleware/test_auth.py
import pytest
from fastapi.testclient import TestClient
from apps.gateway.main import app

client = TestClient(app)


def test_missing_token():
    """测试缺少 Token"""
    response = client.get("/api/v1/sessions")
    assert response.status_code == 401


def test_invalid_token():
    """测试无效 Token"""
    response = client.get(
        "/api/v1/sessions",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
```

Run: `pytest tests/gateway/middleware/test_auth.py -v`

**Step 6: Commit**

```bash
git add apps/gateway/middleware/auth.py apps/gateway/requirements.txt apps/gateway/main.py config/default.yaml tests/gateway/middleware/test_auth.py
git commit -m "feat: integrate keycloak jwt authentication"
```

---

### Task 3: 前端集成 Keycloak

**Files:**
- Modify: `apps/web-ui/package.json`
- Create: `apps/web-ui/src/keycloak.js`
- Modify: `apps/web-ui/src/main.jsx`
- Create: `apps/web-ui/src/components/auth/KeycloakProvider.jsx`
- Create: `apps/web-ui/src/components/auth/UserMenu.jsx`
- Create: `apps/web-ui/src/api/client.js`

**Step 1: 安装依赖**

```bash
cd apps/web-ui
npm install @react-keycloak/web keycloak-js
```

**Step 2: 创建 Keycloak 配置**

```javascript
// apps/web-ui/src/keycloak.js
import Keycloak from 'keycloak-js';

const keycloak = new Keycloak({
  url: 'http://192.168.1.248:8080',
  realm: 'rshAnyGen',
  clientId: 'web-ui'
});

export default keycloak;
```

**Step 3: 创建 Keycloak Provider**

```jsx
// apps/web-ui/src/components/auth/KeycloakProvider.jsx
import { ReactKeycloakProvider } from '@react-keycloak/web';
import keycloak from '../../keycloak';

export default function KeycloakProvider({ children }) {
  const eventLogger = (event, error) => {
    console.log('Keycloak event:', event, error);
  };

  const tokenLogger = (tokens) => {
    console.log('Keycloak tokens updated');
    // 存储 token 到 localStorage
    if (tokens.token) {
      localStorage.setItem('kc_token', tokens.token);
      localStorage.setItem('kc_refreshToken', tokens.refreshToken);
    }
  };

  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      onEvent={eventLogger}
      onTokens={tokenLogger}
      initOptions={{
        onLoad: 'check-sso',
        silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
        pkceMethod: 'S256'
      }}
    >
      {children}
    </ReactKeycloakProvider>
  );
}
```

**Step 4: 更新入口文件**

```jsx
// apps/web-ui/src/main.jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import KeycloakProvider from './components/auth/KeycloakProvider';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <KeycloakProvider>
      <App />
    </KeycloakProvider>
  </React.StrictMode>
);
```

**Step 5: 创建 API 请求拦截器**

```javascript
// apps/web-ui/src/api/client.js
import { useKeycloak } from '@react-keycloak/web';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:9301';

export function useAuthenticatedFetch() {
  const { keycloak } = useKeycloak();

  const authFetch = async (url, options = {}) => {
    // 确保 token 有效
    await keycloak.updateToken(30);

    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${keycloak.token}`,
      ...options.headers
    };

    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers
    });

    if (response.status === 401) {
      // Token 过期,重新登录
      keycloak.login();
    }

    return response;
  };

  return authFetch;
}
```

**Step 6: 创建登录/登出组件**

```jsx
// apps/web-ui/src/components/auth/UserMenu.jsx
import { useKeycloak } from '@react-keycloak/web';

export default function UserMenu() {
  const { keycloak, initialized } = useKeycloak();

  if (!initialized) {
    return <div className="animate-pulse w-8 h-8 bg-gray-200 rounded-full" />;
  }

  if (!keycloak.authenticated) {
    return (
      <button
        onClick={() => keycloak.login()}
        className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-600"
      >
        登录
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium">
        {keycloak.tokenParsed?.preferred_username || '用户'}
      </span>
      <button
        onClick={() => keycloak.logout()}
        className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
      >
        登出
      </button>
    </div>
  );
}
```

**Step 7: 更新 ChatPage 集成认证**

```jsx
// apps/web-ui/src/pages/ChatPage.jsx
import { useKeycloak } from '@react-keycloak/web';
import UserMenu from '../components/auth/UserMenu';

export default function ChatPage() {
  const { keycloak, initialized } = useKeycloak();

  // 等待初始化
  if (!initialized) {
    return <div>加载中...</div>;
  }

  // 未登录则显示登录按钮
  if (!keycloak.authenticated) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">欢迎使用 rshAnyGen</h1>
          <button
            onClick={() => keycloak.login()}
            className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-600"
          >
            登录开始使用
          </button>
        </div>
      </div>
    );
  }

  // 已登录,显示聊天界面
  return (
    <div className="h-screen flex flex-col">
      {/* 顶部导航 */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h1 className="text-xl font-bold">rshAnyGen</h1>
        <UserMenu />
      </div>

      {/* 聊天内容 */}
      {/* ... 现有聊天界面代码 ... */}
    </div>
  );
}
```

**Step 8: Commit**

```bash
git add apps/web-ui/package.json apps/web-ui/src/keycloak.js apps/web-ui/src/main.jsx apps/web-ui/src/components/auth/ apps/web-ui/src/api/client.js apps/web-ui/src/pages/ChatPage.jsx
git commit -m "feat: integrate keycloak authentication in frontend"
```

---

## Phase 2: Token-aware 上下文管理(Week 2)

### Task 4: 实现 Token 计数器

**Files:**
- Create: `apps/shared/token_counter.py`
- Modify: `apps/gateway/requirements.txt`

**Step 1: 添加 tiktoken 依赖**

```bash
echo "tiktoken==0.5.2" >> apps/gateway/requirements.txt
pip install tiktoken
```

**Step 2: 创建 Token 计数器**

```python
# apps/shared/token_counter.py
"""Token 计数工具"""
import tiktoken
from typing import List, Dict
from apps.shared.logger import LogManager

logger_manager = LogManager("token_counter")
logger = logger_manager.get_logger()

# 模型对应的编码器
MODEL_ENCODINGS = {
    "qwen-max": "cl100k_base",
    "qwen-plus": "cl100k_base",
    "gpt-4": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base"
}


class TokenCounter:
    """Token 计数器"""

    def __init__(self, model: str = "qwen-max"):
        encoding_name = MODEL_ENCODINGS.get(model, "cl100k_base")
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.model = model

    def count_text(self, text: str) -> int:
        """计算文本的 token 数"""
        return len(self.encoding.encode(text))

    def count_message(self, message: Dict) -> int:
        """计算单条消息的 token 数"""
        role_tokens = self.count_text(message.get("role", ""))
        content_tokens = self.count_text(message.get("content", ""))
        return role_tokens + content_tokens + 4

    def count_messages(self, messages: List[Dict]) -> int:
        """计算消息列表的总 token 数"""
        total = sum(self.count_message(msg) for msg in messages)
        return total + 3

    def trim_messages_to_limit(
        self,
        messages: List[Dict],
        max_tokens: int,
        min_messages: int = 1
    ) -> List[Dict]:
        """裁剪消息列表以符合 token 限制"""
        if not messages:
            return []

        # 从最新消息开始累加
        trimmed = []
        current_tokens = 0

        for msg in reversed(messages):
            msg_tokens = self.count_message(msg)

            if current_tokens + msg_tokens > max_tokens:
                if len(trimmed) < min_messages:
                    trimmed.append(msg)
                    current_tokens += msg_tokens
                else:
                    break
            else:
                trimmed.append(msg)
                current_tokens += msg_tokens

        # 恢复原始顺序
        return list(reversed(trimmed))


# 全局实例
_counter = None

def get_token_counter(model: str = "qwen-max") -> TokenCounter:
    """获取 Token 计数器单例"""
    global _counter
    if _counter is None or _counter.model != model:
        _counter = TokenCounter(model)
    return _counter
```

**Step 3: 创建测试**

```python
# tests/shared/test_token_counter.py
import pytest
from apps.shared.token_counter import TokenCounter


def test_count_text():
    """测试文本计数"""
    counter = TokenCounter()
    text = "你好世界"
    count = counter.count_text(text)
    assert 4 <= count <= 10


def test_count_message():
    """测试消息计数"""
    counter = TokenCounter()
    message = {"role": "user", "content": "什么是Python?"}
    count = counter.count_message(message)
    assert count > 0


def test_trim_messages():
    """测试消息裁剪"""
    counter = TokenCounter()
    messages = [
        {"role": "user", "content": "问题1"},
        {"role": "assistant", "content": "回答1"},
        {"role": "user", "content": "问题2"},
        {"role": "assistant", "content": "回答2"},
        {"role": "user", "content": "问题3"}
    ]

    trimmed = counter.trim_messages_to_limit(messages, max_tokens=50)
    assert len(trimmed) < len(messages)
    assert trimmed[-1] == messages[-1]
```

Run: `pytest tests/shared/test_token_counter.py -v`

**Step 4: Commit**

```bash
git add apps/shared/token_counter.py tests/shared/test_token_counter.py
git commit -m "feat: add token-aware message counter"
```

---

### Task 5: 实现三级上下文构建器

**Files:**
- Create: `apps/gateway/services/context_builder.py`
- Update: `config/default.yaml`

**Step 1: 更新配置**

```yaml
# config/default.yaml
# 添加上下文配置
context:
  working_memory:
    max_tokens: 2048
    min_turns: 3
    max_turns: 10

  short_term_summary:
    trigger_tokens: 8192
    max_summary_tokens: 512
    topic_change_threshold: 0.7

  long_term_memory:
    retrieval_top_k: 3
    min_importance: 0.6
    max_age_days: 90
```

**Step 2: 创建上下文构建器**

```python
# apps/gateway/services/context_builder.py
"""三级上下文构建器"""
from typing import List, Dict, Optional
from apps.shared.redis_client import RedisOperations
from apps.shared.token_counter import get_token_counter
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("context_builder")
logger = logger_manager.get_logger()

# 配置参数
WORKING_MEMORY_MAX_TOKENS = config.get("context.working_memory.max_tokens", 2048)
WORKING_MEMORY_MIN_TURNS = config.get("context.working_memory.min_turns", 3)
SUMMARY_MAX_TOKENS = config.get("context.short_term_summary.max_summary_tokens", 512)


class ContextBuilder:
    """三级上下文构建器"""

    def __init__(self, model: str = "qwen-max"):
        self.redis = RedisOperations()
        self.token_counter = get_token_counter(model)
        self.model = model

    async def build_context(
        self,
        session_id: str,
        user_id: str,
        current_message: str
    ) -> List[Dict]:
        """构建完整上下文

        三级结构:
        1. 长期记忆(系统提示)
        2. 短期摘要(如果有)
        3. 工作记忆(最近消息)
        4. 当前消息
        """
        await self.redis.init()

        context = []
        total_tokens = 0

        # === 第一层: 长期记忆 ===
        long_term_memory = await self._build_long_term_memory(user_id, current_message)
        if long_term_memory:
            context.append(long_term_memory)
            total_tokens += self.token_counter.count_message(long_term_memory)

        # === 第二层: 短期摘要 ===
        summary = await self._get_session_summary(session_id)
        if summary:
            summary_msg = {
                "role": "system",
                "content": f"【对话摘要】\n{summary}"
            }
            context.append(summary_msg)
            total_tokens += self.token_counter.count_message(summary_msg)

        # === 第三层: 工作记忆 ===
        working_memory = await self._build_working_memory(session_id)
        if working_memory:
            context.extend(working_memory)
            total_tokens += sum(
                self.token_counter.count_message(msg) for msg in working_memory
            )

        # === 第四层: 当前消息 ===
        current_msg = {"role": "user", "content": current_message}
        context.append(current_msg)
        total_tokens += self.token_counter.count_message(current_msg)

        logger.info(
            f"Context built: {len(context)} messages, {total_tokens} tokens "
            f"(working: {len(working_memory)}, summary: {bool(summary)}, "
            f"long_term: {bool(long_term_memory)})"
        )

        return context

    async def _build_long_term_memory(
        self,
        user_id: str,
        current_message: str
    ) -> Optional[Dict]:
        """构建长期记忆系统提示"""
        user_info = await self.redis.client.hgetall(f"user:{user_id}")
        if not user_info:
            return None

        content = f"""【用户信息】
昵称: {user_info.get('nickname', '用户')}
"""

        # 添加用户标签
        tags = await self.redis.client.smembers(f"user:tags:{user_id}")
        if tags:
            content += f"技能标签: {', '.join(tags)}\n"

        return {
            "role": "system",
            "content": content.strip()
        }

    async def _get_session_summary(self, session_id: str) -> Optional[str]:
        """获取会话摘要"""
        summaries = await self.redis.lrange_json(
            f"session:summaries:{session_id}",
            0,
            -1
        )

        if not summaries:
            return None

        # 合并所有摘要段
        summary_parts = []
        for item in summaries:
            topic = item.get("topic", "")
            summary = item.get("summary", "")
            summary_parts.append(f"[{topic}] {summary}")

        return "\n".join(summary_parts)

    async def _build_working_memory(self, session_id: str) -> List[Dict]:
        """构建工作记忆"""
        all_messages = await self.redis.lrange_json(
            f"session:messages:{session_id}",
            0,
            -1
        )

        if not all_messages:
            return []

        # 使用 token counter 裁剪
        working_memory = self.token_counter.trim_messages_to_limit(
            all_messages,
            max_tokens=WORKING_MEMORY_MAX_TOKENS,
            min_messages=WORKING_MEMORY_MIN_TURNS * 2
        )

        return working_memory
```

**Step 3: 创建测试**

```python
# tests/gateway/services/test_context_builder.py
import pytest
from apps.gateway.services.context_builder import ContextBuilder
from apps.gateway.services.message_service import MessageService


@pytest.mark.asyncio
async def test_build_context_empty_session():
    """测试空会话的上下文构建"""
    builder = ContextBuilder()

    context = await builder.build_context(
        session_id="test-empty",
        user_id="user-test",
        current_message="你好"
    )

    assert len(context) >= 1
    assert context[-1]["role"] == "user"
    assert context[-1]["content"] == "你好"


@pytest.mark.asyncio
async def test_build_context_with_history():
    """测试带历史的上下文构建"""
    builder = ContextBuilder()
    message_service = MessageService()

    # 创建历史消息
    session_id = "test-with-history"
    for i in range(5):
        await message_service.save_message(session_id, "user", f"问题{i}")
        await message_service.save_message(session_id, "assistant", f"回答{i}")

    context = await builder.build_context(
        session_id=session_id,
        user_id="user-test",
        current_message="新问题"
    )

    assert len(context) > 1
    assert context[-1]["content"] == "新问题"


@pytest.mark.asyncio
async def test_token_limit():
    """测试 token 限制"""
    builder = ContextBuilder()
    message_service = MessageService()

    # 创建大量长消息
    session_id = "test-token-limit"
    long_content = "这是一个很长的消息内容" * 100
    for i in range(20):
        await message_service.save_message(session_id, "user", long_content)
        await message_service.save_message(session_id, "assistant", long_content)

    context = await builder.build_context(
        session_id=session_id,
        user_id="user-test",
        current_message="新问题"
    )

    # 计算总 token
    total_tokens = sum(
        builder.token_counter.count_message(msg) for msg in context
    )

    # 应该不超过限制
    assert total_tokens <= 3500  # working(2048) + summary(512) + current(~1000)
```

Run: `pytest tests/gateway/services/test_context_builder.py -v`

**Step 4: Commit**

```bash
git add apps/gateway/services/context_builder.py config/default.yaml tests/gateway/services/test_context_builder.py
git commit -m "feat: implement token-aware three-tier context builder"
```

---

### Task 6: 集成上下文构建到聊天流程

**Files:**
- Modify: `apps/gateway/routers/chat.py`

**Step 1: 更新聊天路由**

```python
# apps/gateway/routers/chat.py
from apps.gateway.services.context_builder import ContextBuilder

@router.post("/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """流式聊天接口"""
    user_id = req.state.user_id  # 从 Keycloak JWT 获取
    session_id = request.session_id

    logger.info(f"Chat request: user={user_id}, session={session_id}")

    # 处理会话
    session_service = SessionService()
    message_service = MessageService()
    context_builder = ContextBuilder(model=request.model or "qwen-max")

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

    # 构建上下文 (使用新方法)
    context_messages = await context_builder.build_context(
        session_id=session_id,
        user_id=user_id,
        current_message=request.message
    )

    async def stream_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 流"""
        full_response = ""
        try:
            orchestrator_request = {
                "session_id": session_id,
                "user_id": user_id,
                "message": request.message,
                "chat_history": context_messages,  # 使用构建的上下文
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
                            try:
                                data = json.loads(line)
                                if data.get("type") == "chunk":
                                    full_response += data.get("content", "")
                            except:
                                pass

        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        finally:
            yield "data: [DONE]\n\n"

            # 保存消息
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
            "X-Session-Id": session_id
        }
    )
```

**Step 2: Commit**

```bash
git add apps/gateway/routers/chat.py
git commit -m "feat: integrate context builder into chat flow"
```

---

## Phase 3: 智能摘要生成(Week 3)

### Task 7: 主题切换检测

**Files:**
- Create: `apps/orchestrator/services/topic_detector.py`

**Step 1: 创建主题检测服务**

```python
# apps/orchestrator/services/topic_detector.py
"""主题切换检测服务"""
import numpy as np
from typing import List, Dict
from apps.shared.logger import LogManager

logger_manager = LogManager("topic_detector")
logger = logger_manager.get_logger()


class TopicDetector:
    """主题切换检测器"""

    def __init__(self, embedding_client, threshold: float = 0.7):
        self.embedding_client = embedding_client
        self.threshold = threshold

    async def detect_topic_change(
        self,
        messages: List[Dict],
        lookback: int = 10
    ) -> bool:
        """检测主题是否切换"""
        # 提取用户消息
        user_messages = [
            msg for msg in messages[-lookback:]
            if msg.get("role") == "user"
        ]

        if len(user_messages) < 2:
            return False

        # 获取最近两条用户消息
        recent = user_messages[-2:]

        try:
            # 计算 embedding
            embeddings = await self.embedding_client.embed_batch([
                msg["content"] for msg in recent
            ])

            # 计算余弦相似度
            similarity = self._cosine_similarity(embeddings[0], embeddings[1])

            logger.info(f"Topic similarity: {similarity:.3f} (threshold: {self.threshold})")

            return similarity < self.threshold

        except Exception as e:
            logger.error(f"Topic detection error: {e}")
            return False

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

    async def segment_by_topic(
        self,
        messages: List[Dict],
        min_segment_size: int = 4
    ) -> List[Dict]:
        """按主题分段"""
        if len(messages) < min_segment_size:
            return [{
                "start_idx": 0,
                "end_idx": len(messages) - 1,
                "messages": messages,
                "topic_summary": None
            }]

        segments = []
        current_segment_start = 0

        for i in range(min_segment_size, len(messages)):
            if await self.detect_topic_change(messages[:i+1], lookback=min_segment_size):
                segments.append({
                    "start_idx": current_segment_start,
                    "end_idx": i - 1,
                    "messages": messages[current_segment_start:i],
                    "topic_summary": None
                })
                current_segment_start = i

        # 添加最后一段
        if current_segment_start < len(messages):
            segments.append({
                "start_idx": current_segment_start,
                "end_idx": len(messages) - 1,
                "messages": messages[current_segment_start:],
                "topic_summary": None
            })

        return segments
```

**Step 2: 创建测试**

```python
# tests/orchestrator/services/test_topic_detector.py
import pytest
from apps.orchestrator.services.topic_detector import TopicDetector


class MockEmbeddingClient:
    """模拟 Embedding 客户端"""

    async def embed_batch(self, texts: list) -> list:
        embeddings = []
        for text in texts:
            if "Python" in text:
                embeddings.append([0.9, 0.1] + [0.0] * 1022)
            elif "Java" in text:
                embeddings.append([0.1, 0.9] + [0.0] * 1022)
            else:
                embeddings.append([0.5, 0.5] + [0.0] * 1022)
        return embeddings


@pytest.mark.asyncio
async def test_detect_topic_change():
    """测试主题切换检测"""
    detector = TopicDetector(MockEmbeddingClient(), threshold=0.7)

    # 相同主题
    messages = [
        {"role": "user", "content": "什么是Python装饰器?"},
        {"role": "assistant", "content": "装饰器是..."},
        {"role": "user", "content": "Python装饰器如何使用?"}
    ]

    changed = await detector.detect_topic_change(messages)
    assert changed is False

    # 主题切换
    messages.append({"role": "user", "content": "Java的注解是什么?"})
    changed = await detector.detect_topic_change(messages)
    assert changed is True


@pytest.mark.asyncio
async def test_segment_by_topic():
    """测试主题分段"""
    detector = TopicDetector(MockEmbeddingClient(), threshold=0.7)

    messages = [
        {"role": "user", "content": "Python装饰器1"},
        {"role": "assistant", "content": "回答1"},
        {"role": "user", "content": "Python装饰器2"},
        {"role": "assistant", "content": "回答2"},
        {"role": "user", "content": "Java注解1"},
        {"role": "assistant", "content": "回答3"},
        {"role": "user", "content": "Java注解2"},
        {"role": "assistant", "content": "回答4"},
    ]

    segments = await detector.segment_by_topic(messages, min_segment_size=4)
    assert len(segments) >= 1
```

Run: `pytest tests/orchestrator/services/test_topic_detector.py -v`

**Step 3: Commit**

```bash
git add apps/orchestrator/services/topic_detector.py tests/orchestrator/services/test_topic_detector.py
git commit -m "feat: add topic change detection service"
```

---

### Task 8: 优化摘要生成服务

**Files:**
- Modify: `apps/orchestrator/services/summary_generator.py`

**Step 1: 重构摘要生成器**

```python
# apps/orchestrator/services/summary_generator.py
"""会话摘要生成服务(优化版)"""
from typing import List, Dict
from datetime import datetime
from apps.orchestrator.services.topic_detector import TopicDetector
from apps.shared.redis_client import RedisOperations
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("summary_generator")
logger = logger_manager.get_logger()


class SummaryGenerator:
    """摘要生成器"""

    def __init__(self, llm_client, embedding_client):
        self.llm_client = llm_client
        self.embedding_client = embedding_client
        self.topic_detector = TopicDetector(embedding_client)
        self.redis = RedisOperations()

    async def generate_summary(self, session_id: str) -> List[Dict]:
        """生成会话分段摘要"""
        await self.redis.init()

        # 获取所有消息
        all_messages = await self.redis.lrange_json(
            f"session:messages:{session_id}",
            0,
            -1
        )

        if len(all_messages) < 4:
            return []

        # 按主题分段
        segments = await self.topic_detector.segment_by_topic(all_messages)

        logger.info(f"Segmented session {session_id} into {len(segments)} topics")

        # 为每段生成摘要
        summaries = []
        for segment in segments:
            summary = await self._summarize_segment(segment["messages"])

            segment_summary = {
                "topic": summary.get("topic", "未知主题"),
                "summary": summary.get("summary", ""),
                "message_range": [segment["start_idx"], segment["end_idx"]],
                "created_at": datetime.now().isoformat()
            }
            summaries.append(segment_summary)

        # 保存分段摘要
        await self.redis.client.delete(f"session:summaries:{session_id}")
        for summary in summaries:
            await self.redis.rpush_json(f"session:summaries:{session_id}", summary)

        logger.info(f"Generated {len(summaries)} summaries for session {session_id}")
        return summaries

    async def _summarize_segment(self, messages: List[Dict]) -> Dict:
        """为单个主题段生成摘要"""
        # 格式化消息
        formatted = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "AI"
            formatted.append(f"{role}: {msg['content']}")

        conversation = "\n".join(formatted)

        prompt = f"""请为以下对话生成一个简洁的摘要。

对话内容:
{conversation}

请按以下JSON格式输出(只输出JSON,不要其他内容):
{{
  "topic": "用3-5个字概括主题",
  "summary": "用1-2句话总结关键信息,保留重要决策和结论"
}}
"""

        try:
            response = await self.llm_client.complete(
                prompt,
                max_tokens=200,
                temperature=0.3,
                response_format="json"
            )

            import json
            result = json.loads(response)
            return result

        except Exception as e:
            logger.error(f"Segment summarization error: {e}")
            return {
                "topic": "对话片段",
                "summary": "摘要生成失败"
            }
```

**Step 2: Commit**

```bash
git add apps/orchestrator/services/summary_generator.py
git commit -m "feat: optimize summary generation with topic segmentation"
```

---

## Phase 4: 实体记忆层(Week 4)

### Task 9: 实体提取服务

**Files:**
- Create: `apps/orchestrator/models/entity.py`
- Create: `apps/orchestrator/services/entity_extractor.py`

**Step 1: 定义实体模型**

```python
# apps/orchestrator/models/entity.py
"""实体相关模型"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal


class Entity(BaseModel):
    """实体"""
    entity_id: Optional[str] = None
    type: Literal["person", "project", "event", "location", "concept"]
    name: str = Field(..., min_length=1, max_length=100)
    attributes: Dict = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0, le=1)


class EntityExtraction(BaseModel):
    """实体提取结果"""
    entities: list[Entity]
```

**Step 2: 创建实体提取器**

```python
# apps/orchestrator/services/entity_extractor.py
"""实体提取服务"""
import re
import uuid
from typing import List, Dict
from datetime import datetime

from apps.orchestrator.models.entity import Entity, EntityExtraction
from apps.shared.redis_client import RedisOperations
from apps.shared.logger import LogManager

logger_manager = LogManager("entity_extractor")
logger = logger_manager.get_logger()

# 实体提取规则
ENTITY_PATTERNS = {
    "person": [
        r"(?:我|他|她|他们)(?:是|叫|名字是|叫做)\s*([^\s,，。.!?!\n]{2,10})",
        r"(?:同事|朋友|老师|领导|经理)\s*([^\s,，。.!?!\n]{2,10})",
    ],
    "project": [
        r"(?:项目|系统|产品|应用|平台)(?:叫|名为|是|叫做)\s*([^\s,，。.!?!\n]{2,20})",
    ],
    "location": [
        r"(?:在|位于|从|去|到)\s*((?:北京|上海|广州|深圳|杭州|成都)\w{0,6})",
    ],
    "date": [
        r"\d{4}[-年]\d{1,2}[-月]\d{1,2}[日号]?",
    ],
}


class EntityExtractor:
    """实体提取器(规则 + LLM 混合)"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.redis = RedisOperations()

    async def extract_entities(
        self,
        user_message: str,
        ai_response: str,
        user_id: str,
        session_id: str
    ) -> List[Entity]:
        """提取对话中的实体"""
        entities = []

        # 规则提取
        rule_entities = self._extract_by_rules(user_message)
        entities.extend(rule_entities)

        # LLM 补充(可选)
        if self.llm_client and self._should_use_llm(user_message):
            llm_entities = await self._extract_by_llm(user_message, ai_response)
            entities.extend(llm_entities)

        # 去重合并
        entities = self._deduplicate_entities(entities)

        # 保存到 Redis
        for entity in entities:
            await self._save_entity(entity, user_id, session_id)

        logger.info(f"Extracted {len(entities)} entities from conversation")
        return entities

    def _extract_by_rules(self, text: str) -> List[Entity]:
        """基于规则提取实体"""
        entities = []

        for entity_type, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    entities.append(Entity(
                        type=entity_type,
                        name=match.strip(),
                        confidence=0.8
                    ))

        return entities

    def _should_use_llm(self, text: str) -> bool:
        """判断是否需要用 LLM 提取"""
        keywords = ["是", "叫", "项目", "系统", "名字", "公司", "团队"]
        return any(kw in text for kw in keywords)

    async def _extract_by_llm(
        self,
        user_message: str,
        ai_response: str
    ) -> List[Entity]:
        """使用 LLM 提取实体"""
        conversation = f"用户: {user_message}\nAI: {ai_response}"

        prompt = f"""从以下对话中提取关键实体。

{conversation}

请提取以下类型的实体:
- person: 人名
- project: 项目/系统/产品名称
- location: 地点
- concept: 重要概念/技术

只输出JSON格式(不要其他内容):
{{
  "entities": [
    {{
      "type": "person|project|location|concept",
      "name": "实体名称",
      "attributes": {{"role": "角色"}},
      "confidence": 0.9
    }}
  ]
}}

如果没有实体,返回空数组。"""

        try:
            response = await self.llm_client.complete(
                prompt,
                max_tokens=300,
                temperature=0.2
            )

            import json
            result = json.loads(response)
            extraction = EntityExtraction(**result)
            return extraction.entities

        except Exception as e:
            logger.error(f"LLM entity extraction error: {e}")
            return []

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """去重实体"""
        seen = {}
        for entity in entities:
            key = f"{entity.type}:{entity.name.lower()}"
            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity
        return list(seen.values())

    async def _save_entity(
        self,
        entity: Entity,
        user_id: str,
        session_id: str
    ):
        """保存实体到 Redis"""
        await self.redis.init()

        # 检查是否已存在
        existing_id = await self._find_existing_entity(entity, user_id)

        if existing_id:
            # 更新现有实体
            await self.redis.client.hincrby(
                f"entity:{existing_id}",
                "mention_count",
                1
            )
            await self.redis.client.hset(
                f"entity:{existing_id}",
                "last_mentioned",
                datetime.now().isoformat()
            )
        else:
            # 创建新实体
            entity_id = f"entity-{entity.type}-{uuid.uuid4().hex[:8]}"
            entity_data = {
                "type": entity.type,
                "name": entity.name,
                "attributes": entity.attributes,
                "first_mentioned": datetime.now().isoformat(),
                "last_mentioned": datetime.now().isoformat(),
                "mention_count": 1,
                "confidence": entity.confidence,
                "session_id": session_id
            }

            await self.redis.client.hset(f"entity:{entity_id}", mapping=entity_data)
            await self.redis.client.zadd(
                f"user:entities:{entity.type}:{user_id}",
                {entity_id: int(datetime.now().timestamp())}
            )

    async def _find_existing_entity(
        self,
        entity: Entity,
        user_id: str
    ) -> Optional[str]:
        """查找是否已存在相同实体"""
        await self.redis.init()

        entity_ids = await self.redis.client.zrevrange(
            f"user:entities:{entity.type}:{user_id}",
            0,
            -1
        )

        for entity_id in entity_ids:
            data = await self.redis.client.hgetall(f"entity:{entity_id}")
            if data and data.get("name", "").lower() == entity.name.lower():
                return entity_id

        return None

    async def get_user_entities(
        self,
        user_id: str,
        entity_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """获取用户的实体列表"""
        await self.redis.init()

        if entity_type:
            entity_ids = await self.redis.client.zrevrange(
                f"user:entities:{entity_type}:{user_id}",
                0,
                limit - 1
            )
        else:
            entity_ids = []
            for etype in ["person", "project", "location", "concept"]:
                ids = await self.redis.client.zrevrange(
                    f"user:entities:{etype}:{user_id}",
                    0,
                    limit - 1
                )
                entity_ids.extend(ids)

        entities = []
        for entity_id in entity_ids[:limit]:
            data = await self.redis.client.hgetall(f"entity:{entity_id}")
            if data:
                data["entity_id"] = entity_id
                entities.append(data)

        return entities
```

**Step 3: 创建测试**

```python
# tests/orchestrator/services/test_entity_extractor.py
import pytest
from apps.orchestrator.services.entity_extractor import EntityExtractor


def test_extract_by_rules():
    """测试规则提取"""
    extractor = EntityExtractor()

    text = "我叫张三,在北京工作,负责rshAnyGen项目"
    entities = extractor._extract_by_rules(text)

    assert len(entities) >= 2


@pytest.mark.asyncio
async def test_save_and_retrieve_entities():
    """测试保存和检索实体"""
    extractor = EntityExtractor()

    from apps.orchestrator.models.entity import Entity

    entity = Entity(
        type="person",
        name="李四",
        attributes={"role": "同事"},
        confidence=0.9
    )

    await extractor._save_entity(entity, "user-test", "session-test")
    await extractor._save_entity(entity, "user-test", "session-test")

    entities = await extractor.get_user_entities("user-test", "person")

    assert len(entities) >= 1
    assert entities[0]["name"] == "李四"
    assert int(entities[0]["mention_count"]) == 2
```

Run: `pytest tests/orchestrator/services/test_entity_extractor.py -v`

**Step 4: Commit**

```bash
git add apps/orchestrator/services/entity_extractor.py apps/orchestrator/models/entity.py tests/orchestrator/services/test_entity_extractor.py
git commit -m "feat: add entity extraction service with rule-based and llm hybrid approach"
```

---

## Phase 5: 语义记忆优化(Week 5)

### Task 10: 记忆去重服务

**Files:**
- Modify: `apps/orchestrator/services/memory_service.py`

**Step 1: 添加去重功能**

```python
# apps/orchestrator/services/memory_service.py
# 在 MemoryService 类中添加方法

async def deduplicate_memory(
    self,
    new_content: str,
    user_id: str,
    new_embedding: List[float]
) -> Optional[int]:
    """检查记忆是否重复

    Returns:
        如果重复,返回已存在的记忆 ID;否则返回 None
    """
    # 检索相似记忆(最近30天)
    thirty_days_ago = int(time.time()) - (30 * 24 * 3600)

    results = self.collection.search(
        data=[new_embedding],
        anns_field="vector",
        param={"metric_type": "COSINE", "params": {"ef": 32}},
        limit=5,
        expr=f"user_id == '{user_id}' and created_at >= {thirty_days_ago}",
        output_fields=["id", "content", "importance", "access_count"]
    )

    if not results or not results[0]:
        return None

    for hit in results[0]:
        similarity = 1 - hit.distance

        # 高相似度(>0.92) = 几乎相同
        if similarity > 0.92:
            logger.info(
                f"Found duplicate memory: {hit.id} "
                f"(similarity: {similarity:.3f})"
            )
            await self._update_memory_access(hit.id)
            return hit.id

        # 中等相似度(0.80-0.92) = 需要合并
        elif similarity > 0.80:
            logger.info(
                f"Found similar memory: {hit.id} "
                f"(similarity: {similarity:.3f}), merging..."
            )
            merged_content = await self._merge_memories(
                new_content,
                hit.entity.get("content")
            )
            await self._update_memory_content(hit.id, merged_content)
            return hit.id

    return None


async def save_memory_with_dedup(
    self,
    user_id: str,
    memory: MemoryItem,
    session_id: str,
    embedding: List[float]
):
    """保存记忆(带去重)"""

    # 检查重复
    existing_id = await self.deduplicate_memory(
        memory.content,
        user_id,
        embedding
    )

    if existing_id:
        logger.info(f"Memory deduplicated, using existing: {existing_id}")
        return

    # 保存新记忆
    await self.save_memory(user_id, memory, session_id, embedding)
```

**Step 2: Commit**

```bash
git add apps/orchestrator/services/memory_service.py
git commit -m "feat: add memory deduplication with semantic similarity"
```

---

### Task 11: 时间衰减机制

**Files:**
- Create: `apps/orchestrator/services/memory_scorer.py`
- Modify: `apps/orchestrator/services/background_tasks.py`

**Step 1: 创建记忆评分器**

```python
# apps/orchestrator/services/memory_scorer.py
"""记忆重要性评分器"""
import math
from datetime import datetime
from typing import Dict

from apps.shared.logger import LogManager

logger_manager = LogManager("memory_scorer")
logger = logger_manager.get_logger()


class MemoryScorer:
    """记忆评分器(计算时间衰减后的重要性)"""

    def __init__(self, half_life_days: int = 30):
        self.half_life_days = half_life_days

    def calculate_current_importance(
        self,
        base_importance: float,
        created_at: datetime,
        access_count: int = 0,
        last_accessed: datetime = None
    ) -> float:
        """计算记忆的当前重要性

        公式:
        current_importance = base_importance * time_decay + access_boost
        """
        # 时间衰减(指数衰减)
        days_old = (datetime.now() - created_at).days
        time_decay = math.exp(-days_old / self.half_life_days)

        # 访问频率加成(最多+0.3)
        access_boost = min(access_count * 0.05, 0.3)

        # 最近访问加成
        recent_access_boost = 0
        if last_accessed:
            days_since_access = (datetime.now() - last_accessed).days
            if days_since_access < 7:
                recent_access_boost = 0.2 * (1 - days_since_access / 7)

        # 最终分数
        final_score = min(
            base_importance * time_decay + access_boost + recent_access_boost,
            1.0
        )

        return final_score

    def should_archive(
        self,
        current_importance: float,
        threshold: float = 0.1
    ) -> bool:
        """判断记忆是否应该归档"""
        return current_importance < threshold
```

**Step 2: 添加定时任务**

```python
# apps/orchestrator/services/background_tasks.py
# 添加记忆衰减处理任务

async def _process_memory_decay(self):
    """处理记忆时间衰减"""
    from apps.orchestrator.services.memory_scorer import update_memory_scores
    from apps.orchestrator.services.memory_service import MemoryService

    memory_service = MemoryService()

    while self.running:
        try:
            await self.redis.init()

            # 获取所有用户
            user_keys = await self.redis.client.keys("user:*")
            user_ids = [key.split(":")[1] for key in user_keys if key.startswith("user:") and key.count(":") == 1]

            for user_id in user_ids:
                await update_memory_scores(memory_service, user_id)

            # 每天执行一次
            await asyncio.sleep(24 * 3600)

        except Exception as e:
            logger.error(f"Memory decay processing error: {e}")
            await asyncio.sleep(3600)

# 在 start 方法中添加
async def start(self):
    self.running = True
    logger.info("Background task processor started")

    await asyncio.gather(
        self._process_summaries(),
        self._process_memory_extractions(),
        self._process_memory_decay(),  # 新增
    )
```

**Step 3: Commit**

```bash
git add apps/orchestrator/services/memory_scorer.py apps/orchestrator/services/background_tasks.py
git commit -m "feat: add memory importance scoring with time decay"
```

---

## Phase 6: 最终集成与测试(Week 6)

### Task 12: 端到端集成测试

**Files:**
- Create: `tests/integration/test_complete_flow.py`

**Step 1: 创建完整流程测试**

```python
# tests/integration/test_complete_flow.py
"""完整流程集成测试"""
import pytest
import asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complete_conversation_with_memory():
    """测试带记忆的完整对话流程"""

    # 模拟 Keycloak token
    token = "mock_jwt_token"

    async with AsyncClient(base_url="http://localhost:9301") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. 创建会话
        response = await client.post(
            "/api/v1/sessions",
            json={"user_id": "test-user", "title": "测试会话"},
            headers=headers
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # 2. 发送第一条消息(建立上下文)
        response = await client.post(
            "/api/v1/chat/stream",
            json={
                "message": "我叫张三,是一名Python开发工程师",
                "session_id": session_id
            },
            headers=headers
        )
        assert response.status_code == 200

        # 等待消息保存和实体提取
        await asyncio.sleep(2)

        # 3. 发送第二条消息(测试实体记忆)
        response = await client.post(
            "/api/v1/chat/stream",
            json={
                "message": "我擅长什么?",
                "session_id": session_id
            },
            headers=headers
        )
        # 期望: AI 能记住"Python开发"

        # 4. 切换主题触发摘要
        for i in range(5):
            await client.post(
                "/api/v1/chat/stream",
                json={
                    "message": f"Python问题{i}",
                    "session_id": session_id
                },
                headers=headers
            )

        # 等待摘要生成
        await asyncio.sleep(5)

        # 5. 验证摘要存在
        response = await client.get(
            f"/api/v1/sessions/{session_id}",
            headers=headers
        )
        session_detail = response.json()

        # 6. 创建新会话测试跨会话记忆
        response = await client.post(
            "/api/v1/sessions",
            json={"user_id": "test-user", "title": "新会话"},
            headers=headers
        )
        new_session_id = response.json()["session_id"]

        response = await client.post(
            "/api/v1/chat/stream",
            json={
                "message": "你还记得我叫什么名字吗?",
                "session_id": new_session_id
            },
            headers=headers
        )
        # 期望: AI 能从长期记忆中召回"张三"
```

**Step 2: 性能测试**

```python
# tests/performance/test_context_performance.py
import pytest
import time
from apps.gateway.services.context_builder import ContextBuilder


@pytest.mark.asyncio
async def test_context_build_performance():
    """测试上下文构建性能"""
    builder = ContextBuilder()

    # 准备测试数据(100条消息)
    session_id = "perf-test-session"
    # ... 创建100条消息 ...

    # 测试性能
    start = time.time()

    for i in range(10):
        context = await builder.build_context(
            session_id=session_id,
            user_id="perf-user",
            current_message="测试消息"
        )

    elapsed = time.time() - start
    avg_time = elapsed / 10

    print(f"Average context build time: {avg_time*1000:.2f}ms")

    # 要求平均时间 < 100ms
    assert avg_time < 0.1
```

**Step 3: Commit**

```bash
git add tests/integration/test_complete_flow.py tests/performance/test_context_performance.py
git commit -m "test: add end-to-end and performance tests"
```

---

### Task 13: 文档和部署

**Files:**
- Create: `docs/ARCHITECTURE.md`
- Update: `README.md`

**Step 1: 创建架构文档**

```markdown
# docs/ARCHITECTURE.md

# 系统架构文档

## 整体架构

系统采用三层架构:
- **前端层**: React + Keycloak认证
- **网关层**: FastAPI + JWT验证 + Token-aware上下文管理
- **编排层**: LangGraph + 多服务集成

## 核心优化

### Token-aware 三级上下文管理
1. 工作记忆: 最近3-5轮对话,约2K tokens
2. 短期记忆: 主题感知摘要,约500 tokens
3. 长期记忆: 语义检索相关记忆,约1K tokens

### 三层记忆架构
1. 用户画像层: Redis Hash存储基础信息
2. 实体记忆层: Redis + 规则提取结构化信息
3. 语义记忆层: Milvus向量存储 + 去重 + 时间衰减

### Keycloak OIDC认证
- JWT Token验证
- SSO支持
- 多系统集成能力

## 性能指标

- 上下文构建延迟: P95 < 100ms
- 记忆检索延迟: P95 < 200ms
- Token节省: 40-60%
```

**Step 2: 更新 README**

```markdown
# README.md 更新内容

## 新增功能

### Keycloak 统一认证
- OIDC 标准协议
- JWT Token 验证
- SSO 支持

### Token-aware 上下文管理
- 三级缓存架构
- 动态 Token 裁剪
- 主题感知摘要

### 三层记忆系统
- 用户画像 + 实体记忆 + 语义记忆
- 智能去重
- 时间衰减机制

### 实体提取
- 规则 + LLM 混合提取
- 人名、项目、地点等结构化信息

## 快速开始

### 1. 部署 Keycloak
\`\`\`bash
./scripts/init_keycloak.sh
\`\`\`

### 2. 启动服务
\`\`\`bash
./scripts/dev.sh
\`\`\`

### 3. 访问应用
- Web UI: http://localhost:9300
- Keycloak Admin: http://192.168.1.248:8080/admin
```

**Step 3: Commit**

```bash
git add docs/ARCHITECTURE.md README.md
git commit -m "docs: add architecture documentation and update README"
```

---

## 实施完成总结

实施完成后，系统将具备：

1. **Keycloak OIDC 统一认证**
   - JWT Token 验证
   - SSO 支持
   - 多系统集成能力

2. **Token-aware 三级上下文管理**
   - 工作记忆(2K tokens)
   - 短期摘要(500 tokens)
   - 长期记忆(1K tokens)
   - 节省 40-60% Token 成本

3. **三层记忆架构**
   - 用户画像层(Redis)
   - 实体记忆层(规则+LLM)
   - 语义记忆层(Milvus)
   - 去重 + 时间衰减

4. **智能摘要生成**
   - 主题切换检测
   - 分段摘要
   - 异步生成

5. **性能优化**
   - 上下文构建 P95 < 100ms
   - 记忆检索 P95 < 200ms
