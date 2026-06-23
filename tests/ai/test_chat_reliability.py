"""Failure-path coverage for the chat surface.

Streaming rule (AGENTS.md): any change to streaming must prove a provider failure becomes a
terminal `error` event, never a leaked exception mid-stream.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.cache import InMemoryTTLCache
from app.ai.providers import (
    ProviderConfigError,
    ProviderTimeoutError,
    build_provider,
    get_provider,
)
from app.ai.schemas import ChatMessage, ChatRequest
from app.ai.service import ChatService
from app.core.config import Settings

CHAT_URL = "/api/v1/chat/"
STREAM_URL = "/api/v1/chat/stream"
PAYLOAD = {"messages": [{"role": "user", "content": "boom"}]}


class _BoomProvider:
    """Test-only provider that fails on both paths."""

    name = "boom"

    async def complete(self, messages: list[ChatMessage], *, model: str, temperature: float) -> str:
        raise RuntimeError("provider exploded")

    async def stream(
        self, messages: list[ChatMessage], *, model: str, temperature: float
    ) -> AsyncIterator[str]:
        yield "partial "
        raise RuntimeError("provider exploded mid-stream")


class _SlowProvider:
    """Test-only provider that overruns the request timeout."""

    name = "slow"

    async def complete(self, messages: list[ChatMessage], *, model: str, temperature: float) -> str:
        await asyncio.sleep(1)
        return "never"

    async def stream(
        self, messages: list[ChatMessage], *, model: str, temperature: float
    ) -> AsyncIterator[str]:
        await asyncio.sleep(1)
        yield "late"


def _service(provider: object, *, timeout: float = 30.0) -> ChatService:
    settings = Settings(AI_REQUEST_TIMEOUT=timeout)
    return ChatService(provider=provider, cache=InMemoryTTLCache(max_size=8), settings=settings)  # type: ignore[arg-type]


def _request() -> ChatRequest:
    return ChatRequest(messages=[ChatMessage(role="user", content="boom")])


# ── HTTP surface: failures stay uniform, streams stay well-formed ────────────


async def test_chat_stream_provider_failure_emits_terminal_error(test_app, async_client):
    test_app.dependency_overrides[get_provider] = lambda: _BoomProvider()
    try:
        response = await async_client.post(STREAM_URL, json=PAYLOAD)
        assert response.status_code == 200
        events = [line for line in response.text.splitlines() if line.startswith("event:")]
        assert events[0] == "event: start"
        assert events[-1] == "event: error"
        assert "event: done" not in events
    finally:
        test_app.dependency_overrides.pop(get_provider, None)


async def test_chat_completion_provider_failure_returns_uniform_500(test_app):
    # raise_app_exceptions=False mirrors a real ASGI server: the registered handler's
    # uniform body reaches the client instead of the exception re-raising into the test.
    test_app.dependency_overrides[get_provider] = lambda: _BoomProvider()
    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(CHAT_URL, json=PAYLOAD)
        assert response.status_code == 500
        body = response.json()
        assert body["error"] == "INTERNAL_ERROR"
        assert set(body) >= {"error", "message", "details", "timestamp", "path"}
    finally:
        test_app.dependency_overrides.pop(get_provider, None)


# ── Service unit: timeout enforcement on both paths ──────────────────────────


async def test_complete_times_out_slow_provider():
    service = _service(_SlowProvider(), timeout=0.01)
    with pytest.raises(ProviderTimeoutError) as exc:
        await service.complete(_request())
    assert exc.value.status_code == 504
    assert exc.value.code == "PROVIDER_TIMEOUT"


async def test_stream_times_out_slow_provider_emits_error():
    service = _service(_SlowProvider(), timeout=0.01)
    events = [event async for event in service.stream(_request())]
    assert events[0].event == "start"
    assert events[-1].event == "error"
    assert all(event.event != "done" for event in events)


# ── Provider selection ───────────────────────────────────────────────────────


def test_build_provider_unknown_raises_config_error():
    with pytest.raises(ProviderConfigError) as exc:
        build_provider(Settings(AI_PROVIDER="does-not-exist"))
    assert exc.value.status_code == 500
    assert exc.value.code == "PROVIDER_NOT_CONFIGURED"
