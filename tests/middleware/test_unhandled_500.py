"""Unhandled-exception path: the 'every response' guarantees must hold on a 500.

Starlette's ServerErrorMiddleware renders unhandled 500s *outside* the user middleware
stack, so security headers and the access log are wired to cover that path explicitly.
"""

from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from structlog.testing import capture_logs

from app.ai.providers import get_provider
from app.ai.schemas import ChatMessage

CHAT_URL = "/api/v1/chat/"
PAYLOAD = {"messages": [{"role": "user", "content": "boom"}]}


class _BoomProvider:
    name = "boom"

    async def complete(self, messages: list[ChatMessage], *, model: str, temperature: float) -> str:
        raise RuntimeError("provider exploded")

    async def stream(
        self, messages: list[ChatMessage], *, model: str, temperature: float
    ) -> AsyncIterator[str]:
        raise RuntimeError("provider exploded")
        yield ""  # pragma: no cover


async def test_unhandled_500_gets_security_headers_and_one_access_log(test_app):
    test_app.dependency_overrides[get_provider] = lambda: _BoomProvider()
    # raise_app_exceptions=False mirrors a real ASGI server so the rendered 500 reaches us.
    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    try:
        with capture_logs() as logs:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(CHAT_URL, json=PAYLOAD)
    finally:
        test_app.dependency_overrides.pop(get_provider, None)

    assert response.status_code == 500
    # Security headers present on the unhandled-500 response.
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors" in response.headers["Content-Security-Policy"]
    # Uniform error body still carries request_id.
    body = response.json()
    assert body["error"] == "INTERNAL_ERROR"
    assert body["request_id"] == response.headers["X-Request-ID"]
    # Exactly one access log entry, recorded with status 500 and the request id.
    access = [entry for entry in logs if entry.get("event") == "request"]
    assert len(access) == 1
    assert access[0]["status"] == 500
    assert access[0]["request_id"] == response.headers["X-Request-ID"]
