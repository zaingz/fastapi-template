from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Code before yield runs at startup; code after yield runs at shutdown.
    The application receives traffic only while inside the yield block.

    Extension point: Add database pool init, HTTP client init, etc.
    """
    settings = get_settings()
    configure_logging(json_logs=settings.LOG_JSON, log_level=settings.LOG_LEVEL)

    logger.info(
        "Application starting",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
    )

    # Future extension points:
    # app.state.http_client = httpx.AsyncClient()
    # app.state.db_engine = create_async_engine(...)

    yield

    # Shutdown
    # Future: await app.state.http_client.aclose()
    # Future: await app.state.db_engine.dispose()
    logger.info("Application shutting down")
