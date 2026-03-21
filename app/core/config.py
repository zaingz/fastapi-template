from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "FastAPI Starter"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "A modern FastAPI starter template"
    ENVIRONMENT: Environment = Environment.LOCAL
    DEBUG: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = False

    # Security (placeholder for future auth extension)
    SECRET_KEY: SecretStr = Field(default="change-me-in-production-must-be-32-chars-min")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == Environment.LOCAL


@lru_cache
def get_settings() -> Settings:
    """Singleton settings — reads .env file once."""
    return Settings()
