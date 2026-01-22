"""FastAPI Gateway 服务入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from apps.gateway.middleware.session import SessionMiddleware
from apps.gateway.middleware.auth import JWTAuthMiddleware

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
environment = config.get("app.environment", "development")
cors_origin_regex = None
if environment == "development":
    cors_origin_regex = r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?$"
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "gateway"}


# 注册路由
from apps.gateway.routers import chat, skills, kb, auth, admin_users, sessions

app.include_router(auth.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router)
app.include_router(skills.router)
app.include_router(kb.router)
app.include_router(admin_users.router)
app.include_router(sessions.router)

# 添加会话管理中间件
app.add_middleware(SessionMiddleware)

# 添加 JWT 认证中间件
app.add_middleware(JWTAuthMiddleware)


if __name__ == "__main__":
    import uvicorn

    port = config.get("ports.gateway", 9301)
    uvicorn.run(app, host="0.0.0.0", port=port)
