import asyncio
import hashlib
import json
from collections.abc import AsyncIterator

import structlog

from app.ai.cache import CacheBackend
from app.ai.providers import ChatProvider, ProviderTimeoutError
from app.ai.schemas import ChatRequest, ChatResponse, ChatStreamEvent
from app.core.config import Settings

logger = structlog.get_logger(__name__)


class ChatService:
    """Orchestrates provider calls and caching. Holds no HTTP primitives."""

    def __init__(self, provider: ChatProvider, cache: CacheBackend, settings: Settings) -> None:
        self._provider = provider
        self._cache = cache
        self._ttl = settings.CACHE_TTL
        self._default_model = settings.AI_MODEL
        self._prompt_version = settings.AI_PROMPT_VERSION
        self._timeout = settings.AI_REQUEST_TIMEOUT

    def _resolve_model(self, request: ChatRequest) -> str:
        return request.model or self._default_model

    def _cache_key(self, request: ChatRequest, model: str) -> str:
        # Everything that can change the output must be in the key.
        payload = {
            "provider": self._provider.name,
            "prompt_version": self._prompt_version,
            "model": model,
            "temperature": request.temperature,
            "messages": [m.model_dump() for m in request.messages],
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return f"chat:{digest}"

    async def complete(self, request: ChatRequest) -> ChatResponse:
        model = self._resolve_model(request)
        key = self._cache_key(request, model)

        cached = await self._cache.get(key)
        if cached is not None:
            logger.debug("chat cache hit", key=key)
            return ChatResponse(model=model, content=cached, cached=True)

        try:
            async with asyncio.timeout(self._timeout):
                content = await self._provider.complete(
                    request.messages, model=model, temperature=request.temperature
                )
        except TimeoutError as exc:
            raise ProviderTimeoutError(
                message=f"Provider '{self._provider.name}' timed out after {self._timeout}s"
            ) from exc
        await self._cache.set(key, content, self._ttl)
        return ChatResponse(model=model, content=content, cached=False)

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamEvent]:
        """Yield typed events. Streams are never cached (no-store)."""
        model = self._resolve_model(request)
        yield ChatStreamEvent(event="start", data={"model": model})
        tokens = self._provider.stream(
            request.messages, model=model, temperature=request.temperature
        )
        try:
            while True:
                # Per-token budget: guards against a stalled provider without
                # capping the total length of a legitimately long stream.
                try:
                    async with asyncio.timeout(self._timeout):
                        token = await anext(tokens)
                except StopAsyncIteration:
                    break
                yield ChatStreamEvent(event="token", data={"text": token})
        except Exception as exc:  # surface provider failures as a typed terminal event
            logger.warning("chat stream failed", error=str(exc))
            yield ChatStreamEvent(event="error", data={"message": "stream failed"})
            return
        yield ChatStreamEvent(event="done", data={"model": model})
