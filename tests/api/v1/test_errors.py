from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exception_handlers import register_exception_handlers
from app.core.exceptions import UpstreamRateLimitError


async def test_retry_after_header_rounds_sub_second_up_not_down():
    # int() truncation would send Retry-After: 0 (retry immediately); ceil keeps it >= 1.
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise UpstreamRateLimitError(retry_after=0.5)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "1"


async def test_not_found_error_body_includes_request_id(async_client):
    response = await async_client.get("/api/v1/items/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "NOT_FOUND"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert set(body) >= {"error", "message", "details", "timestamp", "path", "request_id"}


async def test_validation_error_body_includes_request_id(async_client):
    response = await async_client.post("/api/v1/chat/", json={"messages": []})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "VALIDATION_FAILED"
    assert body["request_id"] == response.headers["X-Request-ID"]
