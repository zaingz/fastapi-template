# Production guardrails

What this template guarantees out of the box, what stays opt-in, and where the seams are.
Everything here works with **no API key and no network** on the default `echo` path. Heavy
integrations (Redis, real LLM SDKs, vector DBs, tracing) are **recipes and optional extras**, never
core dependencies — see [`recipes/`](recipes/).

## Request guardrails (always on)

| Guardrail | Mechanism | Setting(s) |
|-----------|-----------|------------|
| MIME sniffing | `X-Content-Type-Options: nosniff` | `SECURITY_HEADERS_ENABLED` |
| Clickjacking | `X-Frame-Options: DENY` + CSP `frame-ancestors` | `CSP_FRAME_ANCESTORS` |
| Referrer leakage | `Referrer-Policy` | `REFERRER_POLICY` |
| Feature access | `Permissions-Policy` | `PERMISSIONS_POLICY` |
| HTTPS pinning | `Strict-Transport-Security` (opt-in) | `HSTS_ENABLED`, `HSTS_MAX_AGE` |
| Host spoofing | `TrustedHostMiddleware` | `ALLOWED_HOSTS` (empty = allow any) |
| Oversized bodies | 413 via `Content-Length` cap | `MAX_REQUEST_BYTES` |
| Per-client flooding | in-process rate limiter (opt-in) | `RATE_LIMIT_*` |

Security headers are set by `app/middleware/security.py` and applied to every response. HSTS is
**off by default** because it is only meaningful over HTTPS — enable it once TLS terminates in front
of the app. Set `ALLOWED_HOSTS` to explicit hostnames in production so a spoofed `Host` header
returns `400` instead of routing.

### Request size

`RequestSizeLimitMiddleware` rejects bodies whose `Content-Length` exceeds `MAX_REQUEST_BYTES`
(default 1 MiB) with a uniform `413`. Bodies sent without a declared length (chunked transfer) are
bounded by the ASGI server's own limits; cap those at the proxy for streaming-upload endpoints.

## Observability

- **Correlation IDs** — `CorrelationIdMiddleware` assigns/propagates `X-Request-ID`. The id is bound
  into structlog contextvars (so every log line in the request carries `request_id`) **and** into
  every error response body, so a client-visible error can be traced to its log line.
- **Access log** — `AccessLogMiddleware` emits exactly one structured log per request with
  `method`, `path`, `status`, `duration_ms`, and `request_id`.
- **Readiness** — `GET /api/v1/health/ready` runs **bounded** checks (cache round-trip, HTTP client
  open) that never make blocking network calls, so the probe can't hang. Add bounded DB/Redis pings
  there as you grow.

## Downstream resilience

A shared `httpx.AsyncClient` is created in the lifespan with explicit per-phase timeouts
(connect/read/write/pool) and pool limits, and exposed via `HttpClientDep`
(`app/core/http_client.py`). Reuse it for all outbound calls so connections pool and a hung upstream
is bounded by the read timeout rather than pinning a worker.

`app/core/resilience.py` provides an **error taxonomy** and a **stdlib retry helper** (no extra
dependency):

- `raise_for_upstream(response)` maps a downstream response to the taxonomy. Only `429/502/503/504`
  become *transient* (retryable) errors; other `4xx/5xx` raise a non-retryable `UpstreamError`.
- `classify_httpx_exception(exc)` maps transport errors — timeouts/connection failures are
  transient, everything else is not.
- `retry_async(op, retries=..., base_delay=..., max_delay=...)` retries **only** classified
  transient failures with exponential backoff + full jitter, honoring `Retry-After` on `429`. There
  is no blanket `except Exception` retry.

```python
from app.core.http_client import HttpClientDep
from app.core.resilience import raise_for_upstream, retry_async

async def fetch_widget(client: HttpClientDep, widget_id: str) -> dict:
    async def call() -> dict:
        resp = raise_for_upstream(await client.get(f"https://api.example.com/widgets/{widget_id}"))
        return resp.json()
    return await retry_async(call, retries=2)
```

Need richer policies (circuit breakers, deadline budgets)? Drop in `tenacity` or `stamina` as an
optional extra and lazy-import it — the stdlib helper is the zero-dependency default.

## Rate limiting

`RateLimiter` is a small Protocol (`app/core/rate_limit.py`); `InMemoryFixedWindowRateLimiter` is the
default, **disabled** unless `RATE_LIMIT_ENABLED=true`. When enabled, `RateLimitMiddleware` limits
per client IP and returns a uniform `429` with `Retry-After` and an `X-RateLimit-Remaining` header.

The in-process limiter counts **per process**, so N replicas allow N× the limit — fine for
single-process dev and conservative protection, not for precise distributed limiting. For that, back
the `RateLimiter` Protocol with Redis: [`recipes/redis-rate-limit.md`](recipes/redis-rate-limit.md).

**Proxy caveat — the limiter keys on the direct peer IP** (`request.client.host`). Behind a load
balancer or reverse proxy that is the *proxy's* IP, so every client collapses into one bucket and the
limit becomes effectively global. To key per real client, run the ASGI server with proxy headers
trusted (e.g. uvicorn `--proxy-headers --forwarded-allow-ips=<proxy-ip>`) so `request.client.host`
reflects the client `X-Forwarded-For` — and only trust those headers when the proxy is the sole
ingress. The limiter also evicts expired buckets once it exceeds an internal key cap, so high client
cardinality (or IP rotation) does not grow memory without bound.

## DDoS: app layer vs. edge

The application layer is **not** a DDoS mitigation and should not pretend to be. Divide
responsibilities:

- **Edge / CDN / proxy (their job)** — volumetric (L3/L4) absorption, SYN-flood protection, IP
  reputation, global rate limiting, geo/ASN blocking, WAF rules, TLS termination, and connection
  caps. Use Cloudflare, AWS Shield/WAF, GCP Cloud Armor, Fastly, etc.
- **App layer (this template's job)** — cheap, correctness-preserving guards so a single abusive
  client can't trivially exhaust a worker: bounded timeouts on outbound calls, request-size cap,
  per-client rate limiting (opt-in), and fast uniform rejections. These reduce blast radius; they do
  not replace edge protection.

Keep liveness (`/health/`) dependency-free so the orchestrator restarts only truly dead processes,
and drain traffic from degraded pods via readiness.

## CORS & SSE

`allow_headers` defaults to a tight allow-list (`Authorization`, `Content-Type`, `X-Request-ID`) —
widen it only as real clients require. SSE consumed via `fetch`/`EventSource` needs no special
request headers. Streaming responses set `Cache-Control: no-store` and `X-Accel-Buffering: no`;
ensure any proxy/CDN in front does not buffer `text/event-stream`.

## Security scanning & dependency hygiene

CI runs a `security` job:

- **Ruff `S` rules** (flake8-bandit) over first-party code — blocking.
- **`pip-audit`** over the locked dependency set — advisory (`continue-on-error`) so a transitive
  CVE awaiting a compatible `fastapi`/`starlette` release doesn't block unrelated merges.

Triage advisories with `uv lock --upgrade` (or `uv lock --upgrade-package <name>`), run
`make check`, and commit the updated `uv.lock`. Promote the audit to blocking once your dependency
floor allows a clean run.
