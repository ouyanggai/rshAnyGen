"""Gateway 配置"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Gateway 配置"""

    # 服务配置
    app_name: str = "rshAnyGen Gateway"
    app_version: str = "0.1.0"

    # 端口配置
    port: int = 9301

    # Redis 配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_ttl: int = 3600

    # 日志配置
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
