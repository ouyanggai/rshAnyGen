"""Gateway 配置"""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from apps.shared.config_loader import ConfigLoader

_config = ConfigLoader()



class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = _config.get("app.name", "rshAnyGen Gateway")
    app_version: str = _config.get("app.version", "0.1.0")
    port: int = _config.get("ports.gateway", 9301)

    redis_host: str = _config.get("dependencies.redis.host", "localhost")
    redis_port: int = _config.get("dependencies.redis.port", 6379)
    redis_db: int = _config.get("dependencies.redis.db", 0)
    redis_ttl: int = _config.get("dependencies.redis.ttl", 3600)

    casdoor_endpoint: str = _config.get("dependencies.casdoor.endpoint", "http://192.168.1.248:8000")
    casdoor_client_id: str = _config.get("dependencies.casdoor.client_id", "2ce83193fbdd8973aa55")
    casdoor_client_secret: str = _config.get("dependencies.casdoor.client_secret", "")
    casdoor_organization_name: str = _config.get("dependencies.casdoor.organization_name", "rsh")
    casdoor_application_name: str = _config.get("dependencies.casdoor.application_name", "rshAnyGen")
    casdoor_redirect_uri: str = _config.get("dependencies.casdoor.redirect_uri", "http://192.168.1.212:9300/callback")

    jwt_algorithm: str = "RS256"
    jwt_issuer: str = _config.get("dependencies.casdoor.endpoint", "http://192.168.1.248:8000")
    jwt_audience: str = _config.get("dependencies.casdoor.client_id", "2ce83193fbdd8973aa55")
    jwt_jwks_url: str = f"{_config.get('dependencies.casdoor.endpoint', 'http://192.168.1.248:8000')}/.well-known/jwks"

    log_level: str = _config.get("app.log_level", "INFO")


settings = Settings()
