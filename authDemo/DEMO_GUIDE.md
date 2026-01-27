# Auth Demo 运行指南

本项目演示了如何使用 Java (Spring Boot) 后端和 Vue 3 前端集成润世华统一登录平台。

## ⚠️ 关键配置说明 (非常重要)

在运行 Demo 之前，请务必确保润世华统一登录平台服务器上的配置与本项目完全一致，否则无法完成鉴权。

**核心配置项：**

*   **Client ID**: `1e27e696c8832ea6bf9f`
*   **Client Secret**: `f2a12262d6116ec505b1d480dcd0eea78fe134d2`
*   **Redirect URL (回调地址)**: `http://192.168.1.212:5174/callback`

> **注意**：请登录润世华统一登录平台管理后台，找到对应的应用 (Application)，在 **Redirect URLs** 列表中添加上述地址。如果地址不匹配，平台将会拒绝认证请求。

---

## 🚀 快速开始

### 1. 启动 Java 后端

后端服务负责处理 OAuth2 流程（获取登录地址、换取 Token、获取用户信息）。

**路径**: `authDemo/java-backend`

```bash
cd authDemo/java-backend

# 运行 Spring Boot 应用 (需要安装 Maven 和 JDK 17+)
mvn spring-boot:run
```

*   **服务端口**: `9306`
*   **API 地址**: `http://localhost:9306/api/auth/...`

### 2. 启动 Vue 前端

前端负责界面展示和用户交互。

**路径**: `authDemo/vue-frontend`

```bash
cd authDemo/vue-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

*   **访问地址**: `http://192.168.1.212:5174` (请使用 IP 访问以匹配回调地址)

---

## 📝 鉴权流程演示

1.  **访问首页**: 浏览器打开 `http://192.168.1.212:5174`。
2.  **点击登录**: 点击 "登录润世华统一登录平台" 按钮。
3.  **跳转认证**: 页面将跳转到润世华统一登录平台。
4.  **用户登录**: 输入用户名密码进行登录。
5.  **回调验证**: 登录成功后，平台将重定向回 `http://192.168.1.212:5174/callback?code=...`。
6.  **展示信息**: 前端将 Code 发送给后端，后端换取 Token 和用户信息，最终在首页展示用户的详细身份信息 (JSON格式)。

## 🛠️ 项目结构

*   `authDemo/java-backend`: 后端代码
    *   `src/main/resources/application.yml`: 配置文件 (包含 Client ID/Secret)
    *   `AuthController.java`: 鉴权接口实现
*   `authDemo/vue-frontend`: 前端代码
    *   `src/App.vue`: 主要 UI 逻辑
    *   `vite.config.js`: 前端配置 (包含代理设置)
