# MaxKey Configuration

> **Status**: ✅ **DEPLOYED** - MaxKey 身份认证平台已部署
> **Last Updated**: 2025-01-22
> **Server Location**: 192.168.1.248

---

## 服务状态

| 服务 | 端口 | 状态 | 用途 |
|------|------|------|------|
| maxkey | 9527 | ✅ Running | 认证服务后端 |
| maxkey-mgt | 9526 | ✅ Running | 管理服务后端 |
| maxkey-frontend | 8527 | ✅ Running | 认证前端界面 |
| maxkey-mgt-frontend | 8526 | ✅ Running | 管理前端界面 |
| maxkey-db | 3307 | ✅ Running | MySQL 数据库 |

---

## 访问地址

| 服务 | URL | 说明 |
|------|-----|------|
| **认证前端** | http://192.168.1.248:8527 | 用户登录界面 |
| **管理前端** | http://192.168.1.248:8526 | 管理控制台 |
| **认证API** | http://192.168.1.248:9527 | OAuth 2.0 / OIDC 端点 |
| **管理API** | http://192.168.1.248:9526 | 管理接口 |

---

## 数据库配置

| 属性 | 值 |
|------|-----|
| **Host** | mysql (Docker 内部) / 192.168.1.248:3307 (外部) |
| **Database** | maxkey |
| **User** | root |
| **Password** | maxkey |
| **Charset** | utf8mb4 |

---

## Docker Compose 配置

**文件位置**: `/root/maxkey/docker-compose.maxkey.yml` on 192.168.1.248

```yaml
version: "3.8"

services:
  mysql:
    image: mysql:8.0.27
    container_name: maxkey-db
    environment:
      MYSQL_ROOT_PASSWORD: maxkey
      MYSQL_DATABASE: maxkey
      TZ: Asia/Shanghai
    ports:
      - "3307:3306"
    volumes:
      - maxkey-db:/var/lib/mysql
      - /root/mysql/logs:/var/log/mysql
    networks:
      - maxkey-net
    restart: unless-stopped
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

  maxkey:
    image: maxkeytop/maxkey:latest
    container_name: maxkey
    environment:
      DATABASE_HOST: mysql
      DATABASE_PORT: 3306
      DATABASE_NAME: maxkey
      DATABASE_USER: root
      DATABASE_PWD: maxkey
      TZ: Asia/Shanghai
    ports:
      - "9527:9527"
    depends_on:
      - mysql
    networks:
      - maxkey-net
    restart: unless-stopped

  maxkey-mgt:
    image: maxkeytop/maxkey-mgt:latest
    container_name: maxkey-mgt
    environment:
      DATABASE_HOST: mysql
      DATABASE_PORT: 3306
      DATABASE_NAME: maxkey
      DATABASE_USER: root
      DATABASE_PWD: maxkey
      TZ: Asia/Shanghai
    ports:
      - "9526:9526"
    depends_on:
      - mysql
    networks:
      - maxkey-net
    restart: unless-stopped

  maxkey-frontend:
    image: maxkeytop/maxkey-frontend:latest
    container_name: maxkey-frontend
    ports:
      - "8527:8527"
    networks:
      - maxkey-net
    restart: unless-stopped

  maxkey-mgt-frontend:
    image: maxkeytop/maxkey-mgt-frontend:latest
    container_name: maxkey-mgt-frontend
    ports:
      - "8526:8526"
    networks:
      - maxkey-net
    restart: unless-stopped

networks:
  maxkey-net:
    driver: bridge

volumes:
  maxkey-db:
```

---

## 默认登录凭据

MaxKey 首次启动后会自动初始化数据库，默认管理员账号：

| 用户类型 | 用户名 | 密码 | 说明 |
|----------|--------|------|------|
| 超级管理员 | admin | (首次登录需设置) | 管理后台登录 |

> **注意**: 首次访问管理后台时，MaxKey 会提示初始化系统并设置管理员密码。

---

## OAuth 2.0 / OIDC 配置

MaxKey 支持 OAuth 2.0 和 OpenID Connect 协议，可通过管理后台配置应用。

### 端点示例

| 端点 | 路径 |
|------|------|
| 授权端点 | /oauth/v20/authorize |
| Token 端点 | /oauth/v20/token |
| 用户信息 | /oauth/v20/me |
| 注销端点 | /oauth/v20/logout |

---

## 管理命令

```bash
# SSH 登录服务器
ssh root@192.168.1.248

# 进入目录
cd /root/maxkey

# 查看服务状态
docker-compose -f docker-compose.maxkey.yml ps

# 查看日志
docker logs maxkey
docker logs maxkey-mgt

# 重启服务
docker-compose -f docker-compose.maxkey.yml restart

# 停止服务
docker-compose -f docker-compose.maxkey.yml down

# 启动服务
docker-compose -f docker-compose.maxkey.yml up -d
```

---

## 与 Keycloak 对比

| 特性 | MaxKey | Keycloak |
|------|--------|----------|
| **开源协议** | Apache 2.0 | Apache 2.0 |
| **开发团队** | 国产 (Dromara) | Red Hat |
| **界面** | 中文友好 | 英文为主 |
| **数据库** | MySQL | PostgreSQL |
| **管理界面** | 独立管理端口 (8526) | 内置 Admin Console |
| **协议支持** | OAuth 2.0, OIDC, SAML, CAS | OAuth 2.0, OIDC, SAML |
| **文档语言** | 中文为主 | 英文 |
| **社区活跃度** | 国内活跃 | 国际活跃 |

---

## 下一步

1. 访问 http://192.168.1.248:8526 完成系统初始化
2. 设置管理员账号
3. 配置应用 (客户端)
4. 测试 OAuth/OIDC 流程
5. 对比 Keycloak 接入体验

---

## 参考文档

- **MaxKey 官网**: https://www.maxkey.org/
- **MaxKey GitHub**: https://github.com/dromara/MaxKey
- **MaxKey Docker 文档**: https://www.maxkey.org/zh/conf/deploy_docker.html
- **Dromara 社区**: https://dromara.org/
