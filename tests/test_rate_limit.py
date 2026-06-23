from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.rate_limit import InMemoryFixedWindowRateLimiter
from app.middleware.rate_limit import RateLimitMiddleware


async def test_limiter_allows_up_to_limit_then_blocks():
    limiter = InMemoryFixedWindowRateLimiter(limit=2, window_seconds=60)
    first = await limiter.acquire("ip")
    second = await limiter.acquire("ip")
    third = await limiter.acquire("ip")
    assert first.allowed and first.remaining == 1
    assert second.allowed and second.remaining == 0
    assert not third.allowed
    assert third.retry_after >= 1


async def test_limiter_keys_are_independent():
    limiter = InMemoryFixedWindowRateLimiter(limit=1, window_seconds=60)
    assert (await limiter.acquire("a")).allowed
    assert not (await limiter.acquire("a")).allowed
    assert (await limiter.acquire("b")).allowed


def _app_with_limiter(limit: int) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        limiter=InMemoryFixedWindowRateLimiter(limit=limit, window_seconds=60),
    )

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"pong": "1"}

    return app


async def test_middleware_returns_429_with_retry_after():
    app = _app_with_limiter(limit=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ok = await client.get("/ping")
        limited = await client.get("/ping")
    assert ok.status_code == 200
    assert ok.headers["X-RateLimit-Remaining"] == "0"
    assert limited.status_code == 429
    assert limited.json()["error"] == "RATE_LIMITED"
    assert int(limited.headers["Retry-After"]) >= 1
