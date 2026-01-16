"""FastAPI Gateway 服务入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from apps.gateway.middleware.session import SessionMiddleware

# 加载配置（全局单例）
config = ConfigLoader()

# 创建全局日志管理器（稍后初始化）
_logger_manager = None


def get_logger():
    """获取或创建全局日志管理器"""
    global _logger_manager
    if _logger_manager is None:
        log_dir = config.get("log_dir", "logs")
        _logger_manager = LogManager("gateway", log_dir=log_dir)
    return _logger_manager.get_logger()


logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Gateway service starting...")

    # 启动
    yield

    # 关闭
    logger.info("Gateway service shutting down...")

    # 清理中间件资源 - 遍历中间件栈找到 SessionMiddleware 并关闭
    for middleware in app.user_middleware:
        if hasattr(middleware, "cls") and middleware.cls == SessionMiddleware:
            # 获取中间件实例并清理
            middleware_stack = app.middleware_stack
            if hasattr(middleware_stack, "apps"):
                for mw in middleware_stack.apps:
                    if isinstance(mw, SessionMiddleware):
                        mw.close()

    # 清理日志管理器
    global _logger_manager
    if _logger_manager:
        _logger_manager.close()
        _logger_manager = None


# 创建 FastAPI 应用
app = FastAPI(
    title=config.get("app.name", "rshAnyGen Gateway"),
    version=config.get("app.version", "0.1.0"),
    description="rshAnyGen API Gateway - 统一入口和会话管理",
    lifespan=lifespan
)

# 配置 CORS（从配置文件读取允许的域名）
cors_origins = config.get("gateway.cors_origins", ["http://localhost:9300"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "gateway"}


# 注册路由
from apps.gateway.routers import chat, skills

app.include_router(chat.router)
app.include_router(skills.router)

# 添加会话管理中间件
app.add_middleware(SessionMiddleware)


if __name__ == "__main__":
    import uvicorn

    port = config.get("ports.gateway", 9301)
    uvicorn.run(app, host="0.0.0.0", port=port)
