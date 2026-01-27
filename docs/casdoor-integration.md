# Casdoor 统一认证接入文档

本文档详细说明了 rshAnyGen 项目如何集成 Casdoor 进行统一身份认证。

## 1. Casdoor 服务端配置

在 Casdoor 管理后台 (例如 `http://192.168.1.248:8000`) 进行以下配置：

### 1.1 创建组织 (Organization)
*   **名称**: `rsh` (示例)
*   **显示名称**: `润小华`

### 1.2 创建应用 (Application)
*   **名称**: `rshAnyGen`
*   **组织**: 选择上面创建的 `rsh`
*   **Client ID**: `2ce83193fbdd8973aa55` (系统生成，需记录)
*   **Client Secret**: `YOUR_CLIENT_SECRET` (系统生成，需记录，**重要**)
*   **Redirect URLs**: 添加前端回调地址
    *   `http://192.168.1.212:9300/callback` (开发/生产环境地址)
    *   `http://localhost:9300/callback` (本地调试地址)
*   **Token Format**: `JWT`
*   **Expire In Hours**: `720` (根据需求设置)

---

## 2. 后端 Gateway 集成

后端主要负责生成登录链接、交换 Token 以及验证 Token 的有效性。

### 2.1 配置文件 (`config/default.yaml`)

修改 `config/default.yaml`，添加 Casdoor 相关配置：

```yaml
dependencies:
  casdoor:
    endpoint: "http://192.168.1.248:8000"          # Casdoor 服务地址
    client_id: "2ce83193fbdd8973aa55"             # Client ID
    client_secret: "YOUR_CLIENT_SECRET"           # Client Secret (必须修改为真实值)
    organization_name: "rsh"                      # 组织名称
    application_name: "rshAnyGen"                 # 应用名称
    redirect_uri: "http://192.168.1.212:9300/callback" # 前端回调地址
```

### 2.2 配置类 (`apps/gateway/config.py`)

映射 YAML 配置到 Python 对象，并设置 JWT 验证参数：

```python
class Settings(BaseSettings):
    # ... 其他配置
    
    # Casdoor 配置
    casdoor_endpoint: str = _config.get("dependencies.casdoor.endpoint", "http://192.168.1.248:8000")
    casdoor_client_id: str = _config.get("dependencies.casdoor.client_id", "")
    casdoor_client_secret: str = _config.get("dependencies.casdoor.client_secret", "")
    casdoor_redirect_uri: str = _config.get("dependencies.casdoor.redirect_uri", "")

    # JWT 验证配置 (适配 Casdoor)
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = casdoor_endpoint  # Casdoor 的 issuer 通常是其 endpoint
    jwt_audience: str = casdoor_client_id
    # 关键：使用标准的 OIDC JWKS 端点
    jwt_jwks_url: str = f"{casdoor_endpoint}/.well-known/jwks"
```

### 2.3 认证路由 (`apps/gateway/routers/auth.py`)

实现标准的 OAuth2 流程接口：

1.  **`/login-url`**: 返回 Casdoor 登录跳转地址。
2.  **`/token`**: 接收前端传来的 `code`，向 Casdoor 换取 `access_token`。
3.  **`/userinfo`**: 解析 Token 或调用 Casdoor 接口获取用户信息。
4.  **`/logout`**: 退出登录接口。

### 2.4 认证中间件 (`apps/gateway/middleware/auth.py`)

使用 `python-jose` 验证 JWT：

1.  **自动获取公钥**: 从 `jwt_jwks_url` (`/.well-known/jwks`) 拉取并缓存公钥。
2.  **Token 验证**: 验证签名、有效期、Issuer 和 Audience。
3.  **异常处理**: 验证失败时直接返回 `401 Unauthorized` JSON 响应，**不要抛出异常**以免造成服务 500 错误。

```python
# 异常处理示例
except (JWTError, ExpiredSignatureError) as e:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid or expired token"},
        headers={"WWW-Authenticate": "Bearer"},
    )
```

---

## 3. 前端 Web UI 集成

前端主要负责引导用户登录、处理回调并保存 Token。

### 3.1 认证上下文 (`CasdoorProvider`)

创建 `apps/web-ui/src/auth/CasdoorProvider.jsx`，用于管理认证状态：
*   初始化时调用后端 `/v1/auth/config` 获取登录配置。
*   提供 `login()` 方法：直接 `window.location.href` 跳转到 Casdoor。
*   提供 `logout()` 方法：清除本地 Token 并刷新页面。

### 3.2 路由守卫 (`AuthGate`)

在 `apps/web-ui/src/components/auth/AuthGate.jsx` 中实现自动跳转：
*   检查用户是否已登录 (`user` 对象是否存在)。
*   如果未登录，**自动调用 `login()`** 跳转至 Casdoor，无需用户点击。
*   加载过程中显示“正在前往集团统一认证平台...”动画。

### 3.3 回调处理 (`AuthCallback`)

创建 `apps/web-ui/src/pages/AuthCallback.jsx` 处理 `/callback` 路由：
1.  从 URL 参数获取 `code`。
2.  调用后端 `/v1/auth/token` 接口，用 `code` 换取 `access_token`。
3.  成功后保存 Token 到 `localStorage` 和 Context，并跳转回首页 `/`。

### 3.4 退出登录

在 `apps/web-ui/src/context/AppContext.jsx` 的 `logout` 方法中：
1.  清除 `user` 和 `accessToken` 状态。
2.  清除 `localStorage`。
3.  **强制刷新页面** (`window.location.href = '/'`)，触发 `AuthGate` 重新进行未登录判定，从而实现“退出后自动跳转回登录页”的效果。

---

## 4. 调试与验证

### 4.1 常用调试命令

*   **查看后端认证配置**:
    ```bash
    curl http://localhost:9301/api/v1/auth/config
    ```
*   **查看 Casdoor OIDC 配置 (确认 JWKS 地址)**:
    ```bash
    curl http://192.168.1.248:8000/.well-known/openid-configuration
    ```

### 4.2 常见问题

1.  **`Unable to find a signing key`**:
    *   原因：Gateway 配置的 JWKS URL 不正确。
    *   解决：确保使用 `/.well-known/jwks` 而不是 `/api/certs`。

2.  **登录后 401 错误**:
    *   原因：Token 验证失败（Audience 不匹配或时钟偏差）。
    *   解决：检查 `config.py` 中的 `jwt_audience` 是否与 Casdoor 的 Client ID 一致。

3.  **退出后页面卡死**:
    *   原因：状态未清除干净，导致死循环或未触发重定向。
    *   解决：在 logout 时强制 `window.location.href = '/'`。

---

## 5. GitLab 集成 (作为应用接入)

如果需要将 GitLab 接入 Casdoor 进行统一登录，请参考以下配置。

### 5.1 Casdoor 侧配置

在 Casdoor 中新建或编辑 GitLab 对应的 **Application**：

*   **Redirect URLs**: 填写 GitLab 的回调地址
    *   格式: `http(s)://<GitLab域名>/users/auth/openid_connect/callback`
    *   示例: `http://192.168.1.100/users/auth/openid_connect/callback`

### 5.2 GitLab 侧配置 (`/etc/gitlab/gitlab.rb`)

配置 `omniauth_providers` 启用 OpenID Connect：

```ruby
gitlab_rails['omniauth_providers'] = [
  {
    name: "openid_connect",
    label: "Casdoor Login",
    args: {
      name: "openid_connect",
      scope: ["openid", "profile", "email"],
      response_type: "code",
      issuer: "http://192.168.1.248:8000",
      discovery: true,
      client_auth_method: "query",
      uid_field: "sub",
      client_options: {
        identifier: "<YOUR_CLIENT_ID>",
        secret: "<YOUR_CLIENT_SECRET>",
        redirect_uri: "http://<GITLAB_URL>/users/auth/openid_connect/callback"
      }
    }
  }
]
```

如果 discovery 失败或需要手动配置 URL，参数如下 (基于当前环境)：

*   **authorize_url**: `http://192.168.1.248:8000/login/oauth/authorize`
*   **token_url**: `http://192.168.1.248:8000/api/login/oauth/access_token`
*   **user_info_url**: `http://192.168.1.248:8000/api/userinfo`

