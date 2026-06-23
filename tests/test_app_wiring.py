from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.core.config import Settings
from app.core.http_client import build_async_client
from app.core.rate_limit import InMemoryFixedWindowRateLimiter


async def test_conditional_guardrails_activate_from_settings(monkeypatch):
    settings = Settings(
        ENVIRONMENT="local",
        DEBUG=True,
        LOG_LEVEL="WARNING",
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_REQUESTS=1,
        ALLOWED_HOSTS=["test"],
        HSTS_ENABLED=True,
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        main_module,
        "get_rate_limiter",
        lambda: InMemoryFixedWindowRateLimiter(limit=1, window_seconds=60),
    )

    application = main_module.create_application()
    application.state.http_client = build_async_client(settings)

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/api/v1/health/")
        second = await client.get("/api/v1/health/")
        bad_host = await client.get("/api/v1/health/", headers={"host": "evil.test"})

    # HSTS now emitted (opt-in), rate limit trips on the 2nd call, bad host rejected.
    assert "Strict-Transport-Security" in first.headers
    assert first.status_code == 200
    assert second.status_code == 429
    assert bad_host.status_code == 400
