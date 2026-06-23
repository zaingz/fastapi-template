import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.cache import get_cache
from app.core.config import Settings, get_settings
from app.core.http_client import build_async_client
from app.core.rate_limit import get_rate_limiter
from app.main import create_application
from app.services.items import _ITEMS


def get_test_settings() -> Settings:
    return Settings(
        ENVIRONMENT="local",
        DEBUG=True,
        LOG_JSON=False,
        LOG_LEVEL="WARNING",
    )


@pytest.fixture(scope="session")
def test_app():
    """Create a test application with overridden settings.

    ASGITransport does not run lifespan events, so the shared HTTP client that the
    lifespan would create is initialized here directly on app.state.
    """
    application = create_application()
    application.dependency_overrides[get_settings] = get_test_settings
    application.state.http_client = build_async_client(get_test_settings())
    return application


@pytest.fixture
async def async_client(test_app):
    """Async HTTP test client backed directly by the ASGI app."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def clear_items():
    """Clear in-memory item store between tests."""
    _ITEMS.clear()
    yield
    _ITEMS.clear()


@pytest.fixture(autouse=True)
def clear_cache():
    """Reset the in-process AI cache between tests."""
    get_cache().clear()
    yield
    get_cache().clear()


@pytest.fixture(autouse=True)
def clear_rate_limiter():
    """Reset the in-process rate limiter between tests."""
    limiter = get_rate_limiter()
    limiter.clear()  # type: ignore[attr-defined]
    yield
    limiter.clear()  # type: ignore[attr-defined]
