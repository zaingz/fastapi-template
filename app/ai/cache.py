import time
from collections import OrderedDict
from functools import lru_cache
from typing import Protocol, runtime_checkable

from app.core.config import Settings, get_settings


@runtime_checkable
class CacheBackend(Protocol):
    """Async key/value cache with TTL. Implementations must be safe to share across requests."""

    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl: int) -> None: ...

    def clear(self) -> None: ...


class InMemoryTTLCache:
    """Per-process exact-match cache with TTL and LRU eviction (stdlib only).

    ponytail: scoped to a single process. Multi-worker/multi-instance deployments that need a
    shared cache should add a Redis backend implementing CacheBackend (docs/architecture.md,
    "Caching tiers"). Default deployments do not need it.
    """

    def __init__(self, *, max_size: int) -> None:
        self._max_size = max_size
        self._store: OrderedDict[str, tuple[float, str]] = OrderedDict()

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    async def set(self, key: str, value: str, ttl: int) -> None:
        self._store[key] = (time.monotonic() + ttl, value)
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()


def build_cache(settings: Settings) -> CacheBackend:
    return InMemoryTTLCache(max_size=settings.CACHE_MAX_SIZE)


@lru_cache
def get_cache() -> CacheBackend:
    """Process-wide cache singleton so entries persist across requests."""
    return build_cache(get_settings())
