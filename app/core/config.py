from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


# Trust-boundary default. A clone that reaches production must override this; the
# validator below refuses to boot with this placeholder when ENVIRONMENT=production.
_INSECURE_SECRET_KEY = "change-me-in-production-must-be-32-chars-min"  # noqa: S105 — placeholder, rejected in prod by validator below


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
    # Allowed request/response headers for CORS. SSE clients using `fetch`/`EventSource`
    # need no special request headers; keep this tight and widen only as clients require.
    CORS_ALLOW_HEADERS: list[str] = ["Authorization", "Content-Type", "X-Request-ID"]

    # Trusted hosts (Host-header allow-list). Empty list = allow any (dev default).
    # In production set explicit hostnames so Host-header spoofing 400s instead of routing.
    ALLOWED_HOSTS: list[str] = []

    # Trust-boundary: reject request bodies larger than this many bytes with 413.
    MAX_REQUEST_BYTES: int = Field(default=1_048_576, gt=0)  # 1 MiB

    # Security response headers
    SECURITY_HEADERS_ENABLED: bool = True
    # `frame-ancestors` value (clickjacking guard). 'none' denies all framing.
    CSP_FRAME_ANCESTORS: str = "'none'"
    REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    PERMISSIONS_POLICY: str = "geolocation=(), microphone=(), camera=()"
    # HSTS is only meaningful over HTTPS; gate it on config so local HTTP is unaffected.
    HSTS_ENABLED: bool = False
    HSTS_MAX_AGE: int = Field(default=31_536_000, ge=0)  # 1 year

    # Security (placeholder for future auth extension)
    SECRET_KEY: SecretStr = Field(default=SecretStr(_INSECURE_SECRET_KEY))

    # Shared outbound HTTP client (lifespan-managed). Explicit timeouts cap each phase so a
    # hung upstream can't pin a worker; limits bound the connection pool.
    HTTP_CONNECT_TIMEOUT: float = Field(default=5.0, gt=0)
    HTTP_READ_TIMEOUT: float = Field(default=30.0, gt=0)
    HTTP_WRITE_TIMEOUT: float = Field(default=10.0, gt=0)
    HTTP_POOL_TIMEOUT: float = Field(default=5.0, gt=0)
    HTTP_MAX_CONNECTIONS: int = Field(default=100, gt=0)
    HTTP_MAX_KEEPALIVE_CONNECTIONS: int = Field(default=20, gt=0)

    # Rate limiting (in-process fixed window). Disabled by default — the local/in-memory
    # limiter is per-process only; multi-instance deploys need a shared backend (see docs).
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = Field(default=60, gt=0)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, gt=0)

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

    @field_validator("CSP_FRAME_ANCESTORS", mode="after")
    @classmethod
    def _quote_csp_keyword(cls, value: str) -> str:
        # CSP keywords (`none`/`self`) are only valid single-quoted; an unquoted `none` is
        # read as a host source and the directive is ignored. python-dotenv strips surrounding
        # quotes from `.env` values, so normalize bare keywords back to their quoted form.
        if value.strip().lower() in {"none", "self"}:
            return f"'{value.strip().lower()}'"
        return value

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
