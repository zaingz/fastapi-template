import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol, runtime_checkable

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after: int  # seconds until the window resets; 0 when allowed


@runtime_checkable
class RateLimiter(Protocol):
    """Fixed-window-style limiter. Implementations must be safe to share across requests.

    `key` identifies the caller (e.g. client IP or API key). A shared backend (Redis)
    is required for correct limiting across multiple processes/instances — see docs.
    """

    async def acquire(self, key: str) -> RateLimitDecision: ...


class InMemoryFixedWindowRateLimiter:
    """Per-process fixed-window counter (stdlib only).

    ponytail: counts live in this process only, so N replicas allow N× the limit. For
    correct distributed limiting add a Redis-backed RateLimiter (see docs/recipes/redis-rate-limit.md).
    """

    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = window_seconds
        self._buckets: dict[str, tuple[float, int]] = {}

    async def acquire(self, key: str) -> RateLimitDecision:
        now = time.monotonic()
        window_start, count = self._buckets.get(key, (now, 0))
        if now - window_start >= self._window:
            window_start, count = now, 0
        retry_after = max(0, int(self._window - (now - window_start)))
        if count >= self._limit:
            return RateLimitDecision(allowed=False, remaining=0, retry_after=retry_after or 1)
        self._buckets[key] = (window_start, count + 1)
        return RateLimitDecision(allowed=True, remaining=self._limit - (count + 1), retry_after=0)

    def clear(self) -> None:
        self._buckets.clear()


def build_rate_limiter(settings: Settings) -> RateLimiter:
    return InMemoryFixedWindowRateLimiter(
        limit=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )


@lru_cache
def get_rate_limiter() -> RateLimiter:
    """Process-wide rate limiter singleton so counts persist across requests."""
    return build_rate_limiter(get_settings())
