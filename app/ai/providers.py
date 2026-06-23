from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Protocol, runtime_checkable

from app.ai.schemas import ChatMessage
from app.core.config import Settings, get_settings
from app.core.exceptions import AppException


class ProviderConfigError(AppException):
    status_code = 500
    code = "PROVIDER_NOT_CONFIGURED"


class ProviderTimeoutError(AppException):
    status_code = 504
    code = "PROVIDER_TIMEOUT"
    message = "The AI provider did not respond in time"


@runtime_checkable
class ChatProvider(Protocol):
    """A chat completion backend. Implementations must be async and HTTP-agnostic.

    `name` participates in the cache key, so distinct providers never collide.
    """

    name: str

    async def complete(
        self, messages: list[ChatMessage], *, model: str, temperature: float
    ) -> str: ...

    def stream(
        self, messages: list[ChatMessage], *, model: str, temperature: float
    ) -> AsyncIterator[str]: ...


def _last_user_text(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return messages[-1].content


class EchoChatProvider:
    """Zero-dependency default provider. Deterministic, no API key, no network.

    Echoes the last user message back as whitespace-delimited tokens so the
    streaming path is exercised end to end out of the box.
    """

    name = "echo"

    async def complete(self, messages: list[ChatMessage], *, model: str, temperature: float) -> str:
        return f"Echo: {_last_user_text(messages)}"

    async def stream(
        self, messages: list[ChatMessage], *, model: str, temperature: float
    ) -> AsyncIterator[str]:
        text = await self.complete(messages, model=model, temperature=temperature)
        tokens = text.split(" ")
        for index, token in enumerate(tokens):
            yield token if index == len(tokens) - 1 else f"{token} "


def build_provider(settings: Settings) -> ChatProvider:
    """Select a provider by `AI_PROVIDER`. `echo` is the always-available default.

    ponytail: real providers (openai, anthropic, litellm) are a documented seam, not bundled —
    they pull heavy SDKs/keys most clones don't need. Upgrade path: add a provider class here
    behind a lazy import and an opt-in extra, keyed by `settings.AI_PROVIDER`.
    See docs/architecture.md ("AI provider seam").
    """
    if settings.AI_PROVIDER == "echo":
        return EchoChatProvider()
    raise ProviderConfigError(
        message=(
            f"AI_PROVIDER='{settings.AI_PROVIDER}' is not built in. Only 'echo' ships by default; "
            "add a provider in app/ai/providers.py (see the seam in docs/architecture.md)."
        )
    )


@lru_cache
def get_provider() -> ChatProvider:
    """Process-wide provider singleton built from settings."""
    return build_provider(get_settings())
