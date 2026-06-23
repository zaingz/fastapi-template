import time

from app.ai.cache import InMemoryTTLCache


async def test_get_returns_stored_value():
    cache = InMemoryTTLCache(max_size=8)
    await cache.set("k", "v", ttl=60)
    assert await cache.get("k") == "v"


async def test_get_missing_key_returns_none():
    cache = InMemoryTTLCache(max_size=8)
    assert await cache.get("missing") is None


async def test_entry_expires_after_ttl(monkeypatch):
    cache = InMemoryTTLCache(max_size=8)
    await cache.set("k", "v", ttl=10)

    base = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: base + 11)
    assert await cache.get("k") is None


async def test_lru_eviction_when_over_max_size():
    cache = InMemoryTTLCache(max_size=2)
    await cache.set("a", "1", ttl=60)
    await cache.set("b", "2", ttl=60)
    await cache.get("a")  # touch "a" so "b" is least-recently-used
    await cache.set("c", "3", ttl=60)

    assert await cache.get("b") is None
    assert await cache.get("a") == "1"
    assert await cache.get("c") == "3"
