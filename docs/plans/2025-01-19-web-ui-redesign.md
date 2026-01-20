# rshAnyGen Web UI 重构设计文档

**日期**: 2025-01-19
**框架**: ChatUI (React) + Vite
**风格**: Soft UI Evolution

---

## 1. 项目概述

### 技术栈
- **构建工具**: Vite 5.x
- **框架**: React 18.x
- **Chat UI**: @chatui/core (Alibaba)
- **样式**: Tailwind CSS 3.x
- **状态管理**: React Context + hooks
- **HTTP客户端**: axios
- **路由**: react-router-dom v6

### 服务端口
- Web UI: 9300
- Gateway API: 9301

---

## 2. UI 设计系统 (Soft UI Evolution)

### 色彩
```css
--primary: #6366F1;         /* AI Purple */
--primary-light: #818CF8;
--primary-dark: #4F46E5;
--secondary: #87CEEB;       /* Soft Blue */
--accent: #F97316;          /* CTA Orange */

--bg-primary: #F8FAFC;
--bg-secondary: #FFFFFF;
--bg-tertiary: #F1F5F9;

--text-primary: #1E293B;
--text-secondary: #475569;
--text-muted: #94A3B8;

--border: #E2E8F0;
```

### 字体 (Geometric Modern)
```css
--font-heading: 'Outfit', sans-serif;
--font-body: 'Work Sans', sans-serif;
```

### 效果
- 过渡: 200-300ms ease
- 阴影: 柔和多层阴影
- 圆角: 8px-20px

---

## 3. 功能模块

### 普通用户功能
1. **聊天页面** - 主聊天界面，SSE流式输出
2. **历史记录** - 对话历史管理
3. **设置页面** - 主题、个人设置

### 管理员功能
1. **模型配置** - LLM提供商配置
2. **技能管理** - 启用/禁用技能
3. **知识库管理** - 文档上传、索引管理

---

## 4. API 集成

### Gateway API (端口 9301)
- `POST /api/v1/chat/stream` - SSE流式聊天
- `GET /api/v1/skills` - 技能列表
- `POST /api/v1/skills/{id}/toggle` - 切换技能

### RAG Pipeline API (端口 9305)
- `POST /api/v1/ingest/file` - 上传文档
- `POST /api/v1/ingest/text` - 摄取文本
- `GET /` - 集合状态

---

## 5. 项目结构

```
apps/web-ui/
├── src/
│   ├── pages/           # 页面组件
│   ├── components/      # UI组件
│   ├── hooks/           # 自定义Hooks
│   ├── api/             # API封装
│   ├── context/         # 状态管理
│   └── styles/          # 样式文件
├── index.html
├── package.json
├── vite.config.js
└── tailwind.config.js
```

---

## 6. 实现优先级

1. 基础项目搭建
2. 聊天页面（核心功能）
3. 历史记录页面
4. 设置页面
5. 管理员功能
6. 样式优化
