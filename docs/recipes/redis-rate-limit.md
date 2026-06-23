# Redis-backed rate limiter

The in-process `InMemoryFixedWindowRateLimiter` counts per process, so N replicas allow N× the
limit. For correct limiting across instances, implement the `RateLimiter` Protocol
(`app/core/rate_limit.py`) against Redis using an atomic counter.

```bash
uv sync --extra redis
```

Settings:

```python
REDIS_URL: SecretStr | None = None
```

`app/core/rate_limit.py`:

```python
class RedisFixedWindowRateLimiter:
    """Distributed fixed-window limiter. Atomic INCR + first-write EXPIRE."""

    def __init__(self, url: str, *, limit: int, window_seconds: int) -> None:
        from redis.asyncio import Redis  # lazy import

        self._redis = Redis.from_url(url, decode_responses=True)
        self._limit = limit
        self._window = window_seconds

    async def acquire(self, key: str) -> RateLimitDecision:
        bucket = f"ratelimit:{key}:{int(time.time()) // self._window}"
        count = await self._redis.incr(bucket)
        if count == 1:
            await self._redis.expire(bucket, self._window)
        ttl = await self._redis.ttl(bucket)
        retry_after = ttl if ttl and ttl > 0 else self._window
        if count > self._limit:
            return RateLimitDecision(allowed=False, remaining=0, retry_after=retry_after)
        return RateLimitDecision(
            allowed=True, remaining=self._limit - count, retry_after=0
        )
```

Wire into `build_rate_limiter()` keyed on `REDIS_URL`. The middleware
(`app/middleware/rate_limit.py`) and the `RateLimitError` taxonomy (`Retry-After` header) are
unchanged — they depend on the Protocol, not the backend.

For smoother limiting under bursts, swap the fixed window for a sliding-window or token-bucket Lua
script evaluated server-side with `EVALSHA` (single atomic round trip). Fixed window is the simplest
correct starting point.
