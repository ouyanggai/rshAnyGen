# rshAnyGen Web UI

基于 [Open WebUI](https://github.com/open-webui/open-webui) 的前端定制版本，为新能源集团定制的 AI Agent 对话界面。

## 定制化内容

### 品牌色彩
- **主色**: #0066CC (蓝色)
- **辅色**: #00B388 (绿色)
- **渐变**: 蓝绿渐变背景

### UI 风格
- Glassmorphism (毛玻璃) 效果
- SvelteKit + TailwindCSS 4.0
- 深色模式支持

### 后端集成
前端通过 SvelteKit hooks 代理 API 请求到 rshAnyGen Gateway:
- **Gateway**: `http://localhost:9301`
- **Orchestrator**: `http://localhost:9302`

## 开发

```bash
# 安装依赖
npm install --legacy-peer-deps

# 开发模式
npm run dev

# 构建
npm run build
```

## 升级上游

从 Open WebUI 上游更新：

```bash
# 拉取上游更新
git fetch upstream
git merge upstream/main

# 解决冲突后提交
git add .
git commit -m "chore: merge upstream updates"
```

## 项目结构

```
web-ui/
├── src/              # SvelteKit 源码
│   ├── routes/       # 页面路由
│   ├── lib/          # 工具库和组件
│   └── hooks.server.ts  # API 代理配置
├── static/           # 静态资源
├── package.json      # 依赖配置
├── vite.config.ts    # Vite 配置
└── tailwind.config.js # TailwindCSS 配置
```

## License

基于 Open WebUI 的 Apache-2.0 License
