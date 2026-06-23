<div align="center">

<h1>⚡ FastAPI AI Template</h1>

<strong>An AI-native FastAPI starter you can run in 30 seconds — streaming, cached chat with no API key and no network, real providers one file away.</strong>

<br/>
<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Typed: mypy --strict](https://img.shields.io/badge/typed-mypy%20--strict-blue.svg)](https://mypy-lang.org/)
[![Lint: ruff](https://img.shields.io/badge/lint-ruff-261230.svg)](https://docs.astral.sh/ruff/)

<br/>

<sub>Python 3.12+ · FastAPI · Pydantic v2 · structlog · uv · Docker · ruff · mypy --strict · pytest</sub>

</div>

---

A **production-shaped FastAPI template for AI applications** — and for the coding agents that build
them. Clone it and a streaming, cached chat API is already running on a deterministic **echo
provider**: no API key, no network, no external services. Real LLMs and a shared cache are clean,
documented opt-in seams — not bundled weight.

## Why this exists

- **AI starters usually don't run on clone.** They demand an API key, a vendor SDK, and a Redis box
  before "hello world." This one answers a real chat request offline, the moment you start it.
- **Templates rot into frameworks.** This stays lean: a working vertical slice with typed config,
  structured logging, uniform errors, and a strict quality gate — building blocks, not bloat.
- **Agents need a contract, not vibes.** [`AGENTS.md`](./AGENTS.md) gives humans and coding agents
  one source of truth — layer rules, recipes, and a `make check` gate that makes "done" verifiable.

## Quick start

> Requires [Python 3.12+](https://www.python.org/) and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/zaingz/fastapi-template.git
cd fastapi-template
make install      # uv sync --all-groups + pre-commit hooks
make dev          # uvicorn on http://localhost:8000  (docs at /docs)
```

No `.env`, no API key. Now talk to the chat API:

```bash
curl -s localhost:8000/api/v1/chat/ \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hello, world"}]}'
```

```json
{ "model": "echo-1", "content": "Echo: Hello, world", "cached": false }
```

## See it work

**Caching** — send the same request again and the service serves it from the in-process cache:

```json
{ "model": "echo-1", "content": "Echo: Hello, world", "cached": true }
```

**Streaming (SSE)** — `POST /api/v1/chat/stream` yields typed events, `start → token* → done`:

```bash
curl -N localhost:8000/api/v1/chat/stream \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hello there"}]}'
```

```text
event: start
data: {"model":"echo-1"}

event: token
data: {"text":"Echo: "}

event: done
data: {"model":"echo-1"}
```

If a provider fails mid-stream, the service emits a terminal `event: error` instead of leaking an
exception. Streams are never cached.

> **Request shape** (`ChatRequest`): `messages` (1–50 items of `{role, content}`, `role` ∈
> `system|user|assistant`, content 1–8000 chars), optional `model` override, optional `temperature`
> (0.0–2.0, default 0.7).

## What's in the box vs. what's a seam

Honesty first — here's exactly what runs today and what's a deliberate, documented extension point.

| ✅ Works offline, today | 🔌 Documented opt-in seam |
|------------------------|---------------------------|
| `echo` provider (`echo-1`), no key/network | Real LLM provider via the `ChatProvider` Protocol |
| Buffered + streaming (SSE) chat | Shared cache / rate limiter via Redis (Protocol-conformant) |
| In-process TTL + LRU response cache | Vector search (pgvector / Qdrant) via a `VectorStore` seam |
| Security headers, request-size cap, Host allow-list | Metrics & tracing (Prometheus / OpenTelemetry) |
| Per-client rate limiting (opt-in, in-process) | Database, auth, queues |
| Shared `httpx` client + retry/backoff + upstream taxonomy | Distributed retries (`tenacity`/`stamina`) |
| Structured access logs + `request_id` in every error | Semantic / vector cache |
| Typed config, uniform errors, health + readiness probes | — |

Seams are wired but not pre-built: you add the class behind a lazy import and an opt-in extra, so the
default install and the test suite stay dependency-free and offline. Runtime deps are deliberately
few: `fastapi[standard]`, `gunicorn`, `structlog`, `asgi-correlation-id`, `uvicorn-worker`, `httpx`.
Production guarantees and copy-paste recipes live in [`docs/production.md`](./docs/production.md) and
[`docs/recipes/`](./docs/recipes/).

## Features

| Area | What's included |
|------|-----------------|
| **AI chat** | Buffered `POST /api/v1/chat/` and streaming `POST /api/v1/chat/stream` (SSE) |
| **Provider seam** | `ChatProvider` Protocol + zero-dependency `EchoChatProvider`; real providers are a lazy, opt-in swap |
| **Caching** | `CacheBackend` Protocol + in-process exact-match TTL **+ LRU** cache; prompt/model/version-aware keys |
| **Typed config** | `pydantic-settings`, `SecretStr` for secrets; one `Settings` object injected via DI |
| **Structured logging** | `structlog` with request correlation IDs; console in dev, JSON in prod |
| **Uniform errors** | `AppException` hierarchy → one consistent JSON error body, incl. `request_id` |
| **Security headers** | `nosniff`, `X-Frame-Options`/CSP `frame-ancestors`, `Referrer-Policy`, `Permissions-Policy`, opt-in HSTS |
| **Trust boundary** | `TrustedHostMiddleware` (Host allow-list) + request-size cap → uniform `413` |
| **Rate limiting** | `RateLimiter` Protocol + in-process limiter (opt-in); `429` + `Retry-After` |
| **Downstream resilience** | Lifespan-managed shared `httpx` client (typed timeouts/limits) + retry/backoff that retries *only* classified transient failures |
| **Versioned API** | URL-based `/api/v1/`; liveness + bounded readiness probes |
| **Middleware** | Correlation ID, structured access log, security headers, request-size, rate limit, timing, CORS |
| **Container** | Multi-stage uv Dockerfile, layer caching, non-root user, healthcheck |
| **Quality gate** | `ruff`, `mypy --strict`, `pytest` + coverage, `pre-commit` — mirrored in CI |
| **Agent-ready** | `AGENTS.md`, `CLAUDE.md`, Copilot instructions, ADRs, vertical-slice recipes |

## Architecture

Layers with a single **inward-only** import direction — `api → services → ai → core`. HTTP lives in
`api/`; business logic in `services/` and `app/ai/`; cross-cutting infrastructure in `core/`.
Services and providers never import HTTP primitives — they raise `AppException` subclasses instead.

```
app/
├── main.py                 # create_application() factory + module-level `app`
├── core/                   # cross-cutting infrastructure (no business logic)
│   ├── config.py           # Settings (pydantic-settings) + get_settings() singleton
│   ├── dependencies.py     # shared Annotated DI aliases
│   ├── exceptions.py       # AppException hierarchy
│   ├── exception_handlers.py
│   ├── lifespan.py         # async startup/shutdown seam
│   └── logging.py          # structlog configuration
├── middleware/             # ASGI middleware (access log, security, request-size, rate limit, timing)
├── ai/                     # AI domain (business logic, no HTTP primitives)
│   ├── schemas.py          # ChatMessage/Request/Response + ChatStreamEvent
│   ├── providers.py        # ChatProvider Protocol + EchoChatProvider + get_provider
│   ├── cache.py            # CacheBackend Protocol + InMemoryTTLCache + get_cache
│   └── service.py          # ChatService: cache lookup/write + provider calls
├── api/v1/                 # versioned HTTP surface
│   ├── router.py           # aggregates endpoint routers under /v1
│   ├── endpoints/          # route handlers (HTTP only; chat.py wires AI DI)
│   └── schemas/            # Pydantic request/response models
└── services/               # non-AI business logic (no HTTP primitives)
```

Full details in [`docs/architecture.md`](./docs/architecture.md).

## AI building blocks

- **Provider seam** — `app/ai/providers.py` defines a `ChatProvider` Protocol (async `complete()` /
  `stream()` + a `name`). `build_provider()` selects by `AI_PROVIDER`; `get_provider()` is the cached
  singleton injected into endpoints. `echo` is the always-available default.
- **Cache key** — `ChatService` hashes provider name, model, `AI_PROMPT_VERSION`, temperature, and
  messages, so changing any input correctly misses the cache. Bump `AI_PROMPT_VERSION` to invalidate.
- **Streaming events** — built on Starlette `StreamingResponse` (no extra dep). The service yields
  typed `start → token* → done` events, serialized as SSE with `Cache-Control: no-store`.
- **Timeout & error semantics** — provider calls are bounded by `AI_REQUEST_TIMEOUT` (default 30s);
  a timeout raises `ProviderTimeoutError`. Streams surface failures as a terminal `error` event
  rather than crashing the connection.

## Agent-ready

This template treats coding agents as first-class contributors — the same contract serves humans.

- **[`AGENTS.md`](./AGENTS.md)** — canonical contract: setup, the `make check` command contract, repo
  map, layer rules, vertical-slice recipes, streaming/caching/testing rules, and Always/Ask-first/Never
  boundaries.
- **[`CLAUDE.md`](./CLAUDE.md)** and **`.github/copilot-instructions.md`** — concise mirrors that defer
  to the same source of truth.
- **Ponytail** working philosophy (climb the ladder: reuse → stdlib → platform feature → installed
  dep → one line) and **Caveman** status prose keep changes minimal, safe, and verifiable — never
  cutting safety carve-outs like trust-boundary validation, typed errors, or secret handling.

## Extending

Each extension mirrors an existing pattern — small, predictable changes. Recipes live in
[`AGENTS.md`](./AGENTS.md); seams and rationale in [`docs/architecture.md`](./docs/architecture.md).

- **Add an endpoint (vertical slice)** — schema → service → endpoint → register → test.
- **Add a real LLM provider** — implement `ChatProvider` with a lazy-imported SDK (opt-in extra),
  wire it into `build_provider()`, add settings (e.g. `OPENAI_API_KEY: SecretStr | None`). Never
  require a key for the `echo` path or for tests.
- **Add a shared cache or rate limiter** — implement `CacheBackend` / `RateLimiter` against Redis;
  the rest of the app is unchanged ([recipes](./docs/recipes/)).
- **Call a downstream service** — inject the shared `HttpClientDep` and wrap calls with
  `retry_async` + `raise_for_upstream` ([`docs/production.md`](./docs/production.md)).

## Deployment

The **container is the portable contract** — the same image runs on any platform that runs containers.

```bash
make docker-build
make docker-run        # serves on :8000 with your .env
```

The ASGI server owns the network bind: `gunicorn.conf.py` reads `$PORT` (default 8000) and
`$WEB_CONCURRENCY` (workers), so platforms that inject `$PORT` work out of the box. Health is at
`/api/v1/health/` and a cache-round-tripping readiness probe at `/api/v1/health/ready` (returns 503
when degraded). Provide secrets via the environment — in production `SECRET_KEY` **must** be
overridden or the app refuses to boot. Platform matrix in [`docs/deployment.md`](./docs/deployment.md).

## Quality gate

```bash
make check        # ruff check + mypy app/ (strict) + pytest — must be green before "done"
```

The same checks run in GitHub Actions on every push and PR; `pre-commit` mirrors them locally.
Individual targets (`make lint`, `make format`, `make typecheck`, `make test`, `make test-cov`) are
in the [`Makefile`](./Makefile).

## Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/chat/` | Chat completion (cached) |
| `POST` | `/api/v1/chat/stream` | Streaming chat completion (SSE) |
| `GET` | `/api/v1/health/` | Liveness probe |
| `GET` | `/api/v1/health/ready` | Readiness probe (bounded cache + HTTP-client checks) |
| `GET` · `POST` | `/api/v1/items/` | List / create — example resource |
| `GET` · `PATCH` · `DELETE` | `/api/v1/items/{id}` | Get / update / delete — example resource |

> Routing uses `redirect_slashes=False`: call paths exactly as shown (trailing slash on `/chat/`,
> none on `/chat/stream`). Interactive docs at `/docs` and `/redoc` when `DEBUG=true`.

**Docs:** [`AGENTS.md`](./AGENTS.md) · [`CONTRIBUTING.md`](./CONTRIBUTING.md) ·
[`SECURITY.md`](./SECURITY.md) · [`docs/architecture.md`](./docs/architecture.md) ·
[`docs/production.md`](./docs/production.md) · [`docs/recipes/`](./docs/recipes/) ·
[`docs/deployment.md`](./docs/deployment.md) ·
[ADR 0001](./docs/adr/0001-template-architecture.md) ·
[ADR 0002](./docs/adr/0002-ai-application-building-blocks.md)

## License

MIT © Zain Ghulam Zada — see [`LICENSE`](./LICENSE).
