from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGENT_STUDIO_",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://agent_studio:agent_studio@localhost:55432/agent_studio"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
