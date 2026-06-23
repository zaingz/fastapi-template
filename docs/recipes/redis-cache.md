# Redis cache backend

The default `InMemoryTTLCache` is per-process: each worker/replica has its own. For a cache shared
across workers and instances, implement `CacheBackend` (`app/ai/cache.py`) against Redis.

```bash
uv sync --extra redis      # `redis` extra is already declared in pyproject.toml
```

Settings:

```python
REDIS_URL: SecretStr | None = None   # e.g. redis://localhost:6379/0
```

`app/ai/cache.py`:

```python
class RedisCache:
    """CacheBackend backed by Redis. Async, shared across workers/instances."""

    def __init__(self, url: str) -> None:
        from redis.asyncio import Redis  # lazy import — keeps default path stdlib-only

        self._redis = Redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ttl: int) -> None:
        await self._redis.set(key, value, ex=ttl)        # SET key value EX ttl

    def clear(self) -> None:
        # No-op for a shared store; flushing a shared DB from app code is dangerous.
        # Scope keys with a prefix and expire via TTL instead.
        ...
```

Wire into `build_cache()`:

```python
def build_cache(settings: Settings) -> CacheBackend:
    if settings.REDIS_URL is not None:
        return RedisCache(settings.REDIS_URL.get_secret_value())
    return InMemoryTTLCache(max_size=settings.CACHE_MAX_SIZE)
```

## `CacheBackend` expectations for Redis-like KV

The Protocol is intentionally minimal — `get`, `set(ttl)`, `clear`. A conforming KV backend must:

- be **async-safe** to share across requests (one client, connection-pooled);
- honor **TTL** server-side (`EX`/`PEXPIRE`) so stale entries expire without app bookkeeping;
- treat values as **opaque strings** (the cache key already encodes provider/model/prompt
  version/temperature/messages — see `ChatService._cache_key`);
- **namespace keys** (prefix) so multiple apps can share one Redis without collisions.

Add a bounded Redis `PING` to `GET /api/v1/health/ready` when you adopt this — see
[`../production.md`](../production.md).
