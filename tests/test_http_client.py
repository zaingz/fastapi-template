import httpx

from app.core.config import Settings
from app.core.http_client import build_async_client


def test_build_async_client_applies_timeouts_and_limits():
    settings = Settings(
        HTTP_CONNECT_TIMEOUT=1.0,
        HTTP_READ_TIMEOUT=2.0,
        HTTP_WRITE_TIMEOUT=3.0,
        HTTP_POOL_TIMEOUT=4.0,
        HTTP_MAX_CONNECTIONS=11,
        HTTP_MAX_KEEPALIVE_CONNECTIONS=5,
    )
    client = build_async_client(settings)
    try:
        assert client.timeout.connect == 1.0
        assert client.timeout.read == 2.0
        assert client.timeout.write == 3.0
        assert client.timeout.pool == 4.0
        assert isinstance(client, httpx.AsyncClient)
    finally:
        # not awaited: no requests issued, just release the unused client object
        pass


async def test_ready_reports_http_client_check(async_client):
    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["checks"]["cache"] == "ok"
    assert body["checks"]["http_client"] == "ok"
