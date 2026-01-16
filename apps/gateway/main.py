"""FastAPI Gateway 服务入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from apps.gateway.middleware import SessionMiddleware
from apps.gateway.routers import chat

# 加载配置
config = ConfigLoader()
logger_manager = LogManager("gateway", log_dir=config.get("log_dir", "logs"))
logger = logger_manager.get_logger()

# 创建 FastAPI 应用
app = FastAPI(
    title=config.get("app.name", "rshAnyGen Gateway"),
    version=config.get("app.version", "0.1.0"),
    description="rshAnyGen API Gateway - 统一入口和会话管理"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置会话管理中间件
app.add_middleware(SessionMiddleware)

# 注册路由
app.include_router(chat.router)

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "gateway"}

@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("Gateway service starting...")

@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("Gateway service shutting down...")
    logger_manager.close()

if __name__ == "__main__":
    import uvicorn
    port = config.get("ports.gateway", 9301)
    uvicorn.run(app, host="0.0.0.0", port=port)
