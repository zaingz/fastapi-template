import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
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
    """Create a test application with overridden settings."""
    application = create_application()
    application.dependency_overrides[get_settings] = get_test_settings
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
