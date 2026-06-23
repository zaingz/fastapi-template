from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


# Trust-boundary default. A clone that reaches production must override this; the
# validator below refuses to boot with this placeholder when ENVIRONMENT=production.
_INSECURE_SECRET_KEY = "change-me-in-production-must-be-32-chars-min"


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

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = False

    # Security (placeholder for future auth extension)
    SECRET_KEY: SecretStr = Field(default=SecretStr(_INSECURE_SECRET_KEY))

    # AI provider — `echo` is the zero-dependency default (no API key, no network).
    AI_PROVIDER: str = "echo"
    AI_MODEL: str = "echo-1"
    AI_PROMPT_VERSION: str = "v1"
    # Wall-clock budget (seconds) for a single provider complete()/stream() token.
    AI_REQUEST_TIMEOUT: float = Field(default=30.0, gt=0)
    OPENAI_API_KEY: SecretStr | None = None

    # AI response cache (in-process exact-match)
    CACHE_TTL: int = 300
    CACHE_MAX_SIZE: int = 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == Environment.LOCAL

    @model_validator(mode="after")
    def _forbid_insecure_secret_in_production(self) -> Self:
        # Data-loss/security carve-out: never let production boot on the shipped placeholder key.
        if self.is_production and self.SECRET_KEY.get_secret_value() == _INSECURE_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY must be overridden when ENVIRONMENT=production "
                "(the default placeholder is insecure)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Singleton settings — reads .env file once."""
    return Settings()
