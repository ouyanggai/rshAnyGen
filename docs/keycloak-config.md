# Keycloak Configuration

> **Status**: ✅ **COMPLETED** - Keycloak 部署和基础配置已完成
> **Last Updated**: 2025-01-22
> **Server Location**: 192.168.1.248:8080

---

## 认证系统对比 (Keycloak vs MaxKey)

| 特性 | Keycloak | MaxKey |
|------|----------|--------|
| **访问地址** | http://192.168.1.248:8080 | http://192.168.1.248:8527 (认证) / 8526 (管理) |
| **管理后台** | http://192.168.1.248:8080/admin | http://192.168.1.248:8526 |
| **数据库** | PostgreSQL (5432) | MySQL (3307) |
| **管理账号** | admin / admin_password | admin / (首次设置) |
| **Realm** | rshAnyGen | 默认应用 |
| **Client (前端)** | web-ui (公开客户端) | 需通过管理后台配置 |
| **Client (后端)** | backend-api (保密客户端) | 需通过管理后台配置 |
| **国内支持** | 英文文档为主 | 国产，中文文档 |
| **协议支持** | OAuth 2.0, OIDC, SAML | OAuth 2.0, OIDC, SAML, CAS |

### 快速对比

| 项目 | Keycloak | MaxKey |
|------|----------|--------|
| **学习曲线** | 中等（英文文档） | 较低（中文文档） |
| **部署复杂度** | 简单 | 简单 |
| **界面友好度** | 国际化 | 中文本土化 |
| **社区支持** | 国际社区活跃 | 国内社区活跃 |
| **企业功能** | 功能全面 | 功能全面 |
| **推荐场景** | 国际化项目 | 国内项目 |

---

## Implementation Progress

### Phase 1: Keycloak Setup (✅ Complete)

| Task | Status | Notes |
|------|--------|-------|
| Keycloak 23.0 deployment | ✅ Done | Docker Compose, PostgreSQL backend |
| Realm rshAnyGen creation | ✅ Done | OIDC enabled |
| Client web-ui configuration | ✅ Done | Public client, Authorization Code flow |
| Client backend-api configuration | ✅ Done | Confidential client, Service accounts enabled |
| JWT authentication middleware | ✅ Done | JWKS caching, token validation |
| Auth router endpoints | ✅ Done | Login, token, refresh, logout, userinfo |
| Gateway integration | ✅ Done | config.py updated with Keycloak settings |

### Backend Integration Files

| File | Purpose | Status |
|------|---------|--------|
| `apps/gateway/middleware/auth.py` | JWT auth middleware with JWKS cache | ✅ Created |
| `apps/gateway/routers/auth.py` | Auth endpoints for frontend integration | ✅ Created |
| `apps/gateway/config.py` | Keycloak configuration | ✅ Updated |
| `config/default.yaml` | Keycloak settings in config | ✅ Updated |

---

## Server Information

| Property | Value |
|----------|-------|
| **Host** | 192.168.1.248:8080 |
| **Admin Console** | http://192.168.1.248:8080/admin |
| **Admin Username** | admin |
| **Admin Password** | admin_password |
| **Realm** | rshAnyGen |
| **Deployment Path** | /root/keycloak on 192.168.1.248 |

### Docker Services Status

```bash
# Check container status
ssh root@192.168.1.248 "cd /root/keycloak && docker-compose -f docker-compose.keycloak.yml ps"

# Expected output:
# NAME            STATUS         PORTS
# keycloak        running        0.0.0.0:8080->8080/tcp
# keycloak-db     running        5432/tcp
```

---

## Realm Configuration: rshAnyGen

| Property | Value |
|----------|-------|
| **Realm Name** | rshAnyGen |
| **Enabled** | true |
| **SSL Required** | None (HTTP only) |
| **Login Theme** | keycloak |
| **Internationalization** | Enabled (English, Chinese) |

### Realm Endpoints

| Endpoint | URL |
|----------|-----|
| **OIDC Discovery** | http://192.168.1.248:8080/realms/rshAnyGen/.well-known/openid-configuration |
| **Token Endpoint** | http://192.168.1.248:8080/realms/rshAnyGen/protocol/openid-connect/token |
| **Authorization** | http://192.168.1.248:8080/realms/rshAnyGen/protocol/openid-connect/auth |
| **Logout** | http://192.168.1.248:8080/realms/rshAnyGen/protocol/openid-connect/logout |
| **JWKS (Public Keys)** | http://192.168.1.248:8080/realms/rshAnyGen/protocol/openid-connect/certs |
| **Issuer** | http://192.168.1.248:8080/realms/rshAnyGen |
| **UserInfo** | http://192.168.1.248:8080/realms/rshAnyGen/protocol/openid-connect/userinfo |

---

## Client Configuration

### web-ui (Frontend Client)

| Property | Value |
|----------|-------|
| **Client ID** | web-ui |
| **Client Type** | Public |
| **Standard Flow Enabled** | true |
| **Direct Access Grants** | false |
| **Implicit Flow Enabled** | false |
| **Valid Redirect URIs** | http://localhost:9300/* (开发默认) |
| **Valid Web Origins** | http://localhost:9300 (开发默认) |
| **Web Origins** | + |

#### 通过局域网 IP 访问 Web UI（必须加白名单）

如果你不是用 `http://localhost:9300` 打开，而是用类似 `http://192.168.1.212:9300` 访问，则需要在 Keycloak 管理台为 `web-ui` client 额外添加：

- **Valid Redirect URIs**：`http://192.168.1.212:9300/*`
- **Valid Web Origins**：`http://192.168.1.212:9300`（或保持 `+`）

否则会出现登录回调失败、或前端一直停留在“正在初始化...”的现象。

### backend-api (Backend Service Client)

| Property | Value |
|----------|-------|
| **Client ID** | backend-api |
| **Internal ID** | b128f20c-b2b8-4620-81cb-ee831681deb5 |
| **Client Type** | Confidential |
| **Client Secret** | backend-secret-123456 |
| **Service Accounts Enabled** | true |
| **Authorization Enabled** | true |
| **Direct Access Grants** | true |
| **Valid Redirect URIs** | http://localhost:8000/* |

---

## Backend Integration

### Gateway Configuration (`apps/gateway/config.py`)

```python
keycloak_url: str = "http://192.168.1.248:8080"
keycloak_realm: str = "rshAnyGen"
keycloak_client_id: str = "backend-api"
keycloak_client_secret: str = "backend-secret-123456"
```

### Keycloak Admin API 权限（用户管理必需）

Web UI 的“用户管理”页面会调用 Gateway 的 admin-only 接口，Gateway 再去调用 Keycloak Admin API。

推荐（生产正确做法）：

1. 进入 Keycloak → Clients → `backend-api`
2. 打开 **Service accounts roles**
3. 给该 service account 分配 `realm-management` 下的权限（至少需要 `view-users` / `manage-users`，以及按需的 `view-realm`、`manage-realm` 等）

开发兜底（仅开发，避免在生产使用 master 管理员密码）：

- 启动 Gateway 时设置环境变量：`KEYCLOAK_ADMIN_USERNAME` / `KEYCLOAK_ADMIN_PASSWORD`
- 当 `backend-api` service account 遇到 403 时，Gateway 会回退用 master realm 的 `admin-cli` 获取 token 再重试

### JWT Middleware (`apps/gateway/middleware/auth.py`)

The JWT authentication middleware:
- Caches JWKS public keys (refreshes every 300 seconds)
- Validates RS256 signatures
- Verifies issuer, audience, and expiration
- Excludes public paths from auth requirement

**Excluded Paths:**
- `/health`
- `/docs`, `/redoc`, `/openapi.json`
- `/auth/login`, `/auth/callback`

### Auth Router Endpoints (`apps/gateway/routers/auth.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login-url` | GET | Get Keycloak login URL for frontend |
| `/auth/login` | POST | Exchange authorization code for tokens |
| `/auth/token` | POST | Client credentials flow (backend-to-backend) |
| `/auth/refresh` | POST | Refresh access token |
| `/auth/logout` | POST | Logout and invalidate tokens |
| `/auth/userinfo` | GET | Get user info from access token |
| `/auth/config` | GET | Get public Keycloak configuration |
| `/auth/introspect` | POST | Introspect and validate token |

---

## API Usage Examples

### Get Login URL (Frontend)

```bash
curl http://localhost:8000/auth/login-url?redirect_uri=http://localhost:9300/callback
```

### Exchange Code for Tokens

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "code": "authorization_code_from_keycloak",
    "redirect_uri": "http://localhost:9300/callback"
  }'
```

### Client Credentials Flow (Backend)

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials"
  }'
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your_refresh_token"
  }'
```

---

## Testing Commands

### Verify Realm

```bash
curl -s http://192.168.1.248:8080/realms/rshAnyGen | jq -r '.realm'
# Expected output: rshAnyGen
```

### Get Admin Token

```bash
ACCESS_TOKEN=$(curl -s -X POST \
  http://192.168.1.248:8080/realms/master/protocol/openid-connect/token \
  -d 'client_id=admin-cli' \
  -d 'username=admin' \
  -d 'password=admin_password' \
  -d 'grant_type=password' | jq -r '.access_token')

echo "Token: ${ACCESS_TOKEN:0:30}..."
```

### List Clients

```bash
curl -s "http://192.168.1.248:8080/admin/realms/rshAnyGen/clients" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[].clientId'
```

### Check Specific Client

```bash
curl -s "http://192.168.1.248:8080/admin/realms/rshAnyGen/clients?clientId=web-ui" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.[0] | {clientId, clientId, publicClient}'
```

---

## Known Issues

### Admin Console Frontend Error

**Symptom**: `net::ERR_BLOCKED_BY_RESPONSE.NotSameOrigin` when accessing admin console

**Root Cause**: Keycloak 23 third-party cookies issue in HTTP environment

**Impact**: Admin UI may have rendering issues, but all API endpoints work correctly

**Workaround**: Use Admin API directly or ignore console errors. Backend functionality is unaffected.

### HTTP Mode (No SSL)

**Current Configuration**: HTTP only, no SSL/TLS

**Note**: This is suitable for development/internal network. For production, enable HTTPS with proper certificates.

### 跨站点 HTTP 登录会失败（Secure Cookie 原因）

如果 Keycloak 与 Web UI 不在同一个站点（例如 Keycloak 在 `192.168.1.248:8080`，Web UI 在 `192.168.1.212:9300`），浏览器会把 Keycloak 视为第三方站点。此时 Keycloak 为了兼容第三方 Cookie，会设置 `SameSite=None; Secure` 的 Cookie。

在 **HTTP**（非 HTTPS）环境下，浏览器通常会拒收/不发送带 `Secure` 的 Cookie，导致表现为：

- 登录页能打开，但登录后反复跳转/回调失败
- 前端一直停留在“正在初始化...”
- 控制台出现 `requestStorageAccess: May not be used in an insecure context`

可选解决方案（推荐优先级从高到低）：

1. 给 Keycloak 和 Web UI 都启用 HTTPS（最稳妥）
2. 把 Keycloak 反向代理到与 Web UI 同域名/同站点下（减少第三方 Cookie 问题）
3. 仅开发：在浏览器里放宽第三方 Cookie/安全策略（不建议长期使用）

### 前端一直显示“正在初始化...”

排查顺序：

1. 先看 Network：`/api/v1/auth/config` 是否能 200 返回（不需要登录）。  
2. 如果你是用局域网 IP 访问（如 `http://192.168.x.x:9300`），按上面的“通过局域网 IP 访问 Web UI”把 redirect/origin 放行。  
3. HTTP 环境下 Keycloak 可能会出现第三方 Cookie 探测报错（`requestStorageAccess: May not be used in an insecure context`），通常不影响“顶层重定向登录”；若仍卡住，建议改用 HTTPS 或关闭浏览器对第三方 Cookie 的严格限制用于开发测试。

---

## 管理员用户（用于进入 /admin/users）

Web UI 的 `/admin/users` 页面会检查当前用户是否拥有 realm 角色 `admin`。

在 Keycloak 管理台创建/配置步骤：

1. 打开 `http://192.168.1.248:8080/admin` 并登录 master 管理员
2. 选择 realm：`rshAnyGen`
3. 进入 **Realm roles**，确认存在 `admin`（没有就创建）
4. 进入 **Users**，创建一个用户并设置密码（Credentials）
5. 在该用户的 **Role mapping** 中分配 realm 角色 `admin`

---

## External Services

### Redis (192.168.1.248)

| Property | Value |
|----------|-------|
| **Host** | 192.168.1.248 |
| **Port** | 6379 |
| **Status** | ✅ Available (pre-existing service) |
| **Purpose** | Conversation caching, working memory storage |

### Redis Configuration in Gateway

```yaml
# config/default.yaml
dependencies:
  redis:
    host: "192.168.1.248"
    port: 6379
```

### Redis Client Wrapper

File: `apps/shared/redis_client.py`

```python
class RedisClient:
    """Redis 客户端封装，支持 JSON 操作"""
    # Supports: lists, hashes, sets, sorted sets
```

### Redis Data Structures (Planned)

| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `conv:{user_id}:{conv_id}` | Working memory (recent messages) | 24h |
| `summary:{user_id}:{conv_id}` | Short-term summary | 7d |
| `session:{user_id}` | User session data | 1h |

---

## Next Steps

### Remaining Tasks (Phase 2-6)

1. **Phase 2: Redis + Context Builder** (In Progress)
   - Token counter implementation ✅
   - Redis client wrapper ✅
   - Context builder service ✅
   - Redis connection testing (remote server) - **TODO**
   - Integration testing needed

2. **Phase 3: Memory Manager** (Pending)
   - Long-term memory storage
   - Short-term summary generation
   - Memory retrieval logic

3. **Phase 4: Database Schema** (Pending)
   - Conversations table
   - Messages table
   - User profiles table
   - Memory embeddings table

4. **Phase 5: Orchestration Integration** (Pending)
   - LangGraph state management
   - RAG with context
   - Agent integration

5. **Phase 6: Testing & Documentation** (Pending)
   - E2E testing
   - Performance testing
   - User documentation

### Immediate Actions

1. Test Keycloak auth flow with actual frontend
2. Implement Redis-based conversation storage
3. Create memory manager service
4. Update orchestrator to use context builder

---

## References

- **Implementation Plan**: `docs/plans/2025-01-22-conversation-memory-implementation-v2.md`
- **Keycloak Docs**: https://www.keycloak.org/documentation
- **OIDC RFC**: https://openid.net/connect/
