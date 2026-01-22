"""Gateway 配置"""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from apps.shared.config_loader import ConfigLoader

_config = ConfigLoader()


def _default_jwt_issuer() -> str:
    url = _config.get("dependencies.keycloak.url", "http://192.168.1.248:8080")
    realm = _config.get("dependencies.keycloak.realm", "rshAnyGen")
    return f"{url}/realms/{realm}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = _config.get("app.name", "rshAnyGen Gateway")
    app_version: str = _config.get("app.version", "0.1.0")
    port: int = _config.get("ports.gateway", 9301)

    redis_host: str = _config.get("dependencies.redis.host", "localhost")
    redis_port: int = _config.get("dependencies.redis.port", 6379)
    redis_db: int = _config.get("dependencies.redis.db", 0)
    redis_ttl: int = _config.get("dependencies.redis.ttl", 3600)

    keycloak_url: str = _config.get("dependencies.keycloak.url", "http://192.168.1.248:8080")
    keycloak_realm: str = _config.get("dependencies.keycloak.realm", "rshAnyGen")
    keycloak_frontend_client_id: str = _config.get("dependencies.keycloak.frontend_client_id", "web-ui")
    keycloak_backend_client_id: str = _config.get("dependencies.keycloak.backend_client_id", "backend-api")
    keycloak_backend_client_secret: str = _config.get("dependencies.keycloak.backend_client_secret", "")
    keycloak_admin_username: Optional[str] = None
    keycloak_admin_password: Optional[str] = None

    jwt_algorithm: str = "RS256"
    jwt_issuer: str = _default_jwt_issuer()
    jwt_audience: str = "account"

    log_level: str = _config.get("app.log_level", "INFO")


settings = Settings()
