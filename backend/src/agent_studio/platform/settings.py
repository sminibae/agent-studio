from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGENT_STUDIO_",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str = (
        "postgresql+psycopg://agent_studio:agent_studio@localhost:5432/agent_studio"
    )
    proxy_shared_secret: SecretStr | None = None
    allowed_auth_issuer: str | None = None
    allowed_auth_subject: str | None = None
    development_auth_issuer: str = "https://development.agent-studio.local"
    development_auth_subject: str = "local-developer"
    development_auth_email: str = "developer@localhost"
    development_auth_name: str = "Local Developer"


@lru_cache
def get_settings() -> Settings:
    return Settings()
