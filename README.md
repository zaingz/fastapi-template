<div align="center">

<h1>⚡ FastAPI AI Template</h1>

<strong>An AI-native, agent-ready FastAPI starter you can ship today.</strong>

<em>Clone it and you already have a streaming, cached chat API running — no API key, no network, no external services.</em>

<br/>
<br/>

<code>AI-native</code> · <code>agent-ready</code> · <code>batteries-included</code> · <code>streaming</code> · <code>response caching</code> · <code>deployment-ready</code>

<br/>

<sub>Python 3.12+ • FastAPI • Pydantic v2 • structlog • uv • Docker • ruff • mypy --strict • pytest</sub>

</div>

---

## What is this?

A **production-shaped FastAPI template built for AI applications** — and for the coding agents that
increasingly build them. It ships the core building blocks you need to start an AI backend in
seconds, without the bloat of an opinionated framework:

- a **chat API** with both buffered and **streaming (SSE)** responses,
- a **provider seam** so you swap the built-in fake model for a real LLM in one small file,
- a **response cache** with a clean upgrade path from in-process to shared,
- a **rigorous agent playbook** (`AGENTS.md` / `CLAUDE.md`) so humans *and* AI agents extend it correctly.

The default path runs entirely offline on a deterministic **Echo provider**, so the template works
the moment you clone it and the test suite needs zero secrets.

## Why you'll like it

**For developers**
- Skip the boilerplate: typed config, structured logging, uniform errors, versioned API, Docker,
  and CI are already wired.
- A real, working AI vertical slice to copy — not a hello-world stub.
- One portable contract for deploy: the container runs the same everywhere.

**For coding agents**
- `AGENTS.md` is a single, concrete source of truth: command contract, layer invariants, vertical-
  slice recipes, and Always/Ask-first/Never boundaries.
- A **Ponytail-inspired** working philosophy keeps changes minimal and safe.
- A strict, fast quality gate (`make check`) makes "done" verifiable, not vibes.

## Quick start

> Requires [Python 3.12+](https://www.python.org/) and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/zaingz/fastapi-template.git
cd fastapi-template
make install      # uv sync --all-groups + pre-commit hooks
make dev          # uvicorn on http://localhost:8000  (docs at /docs)
```

That's it — no `.env` or API key needed to run the default Echo provider.

### Talk to the chat API (no key required)

**Buffered completion** — `POST /api/v1/chat/`

```bash
curl -s localhost:8000/api/v1/chat/ \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hello, world"}]}'
```

```json
{ "model": "echo-1", "content": "Echo: Hello, world", "cached": false }
```

Send the same request again and you get `"cached": true`.

**Streaming completion (SSE)** — `POST /api/v1/chat/stream`

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

event: token
data: {"text":"Hello "}

event: token
data: {"text":"there"}

event: done
data: {"model":"echo-1"}
```

**Request shape** (`ChatRequest`): `messages` (1–50 items of `{role, content}`, `role` ∈
`system|user|assistant`, content 1–8000 chars), optional `model` override, optional `temperature`
(0.0–2.0, default 0.7).

## Features

| Area | What's included |
|------|-----------------|
| **AI chat** | Buffered `POST /api/v1/chat/` and streaming `POST /api/v1/chat/stream` (Server-Sent Events) |
| **Provider seam** | `ChatProvider` Protocol with a zero-dependency `EchoChatProvider` default; real providers are a lazy, opt-in swap |
| **Caching** | `CacheBackend` Protocol + in-process TTL **+ LRU** cache; prompt/model/version-aware keys; streams never cached |
| **Typed config** | `pydantic-settings` with `SecretStr` for secrets; one `Settings` object, injected via DI |
| **Structured logging** | `structlog` with request correlation IDs; console in dev, JSON in prod |
| **Uniform errors** | `AppException` hierarchy → one consistent JSON error body |
| **Versioned API** | URL-based `/api/v1/`; health & readiness probes |
| **Middleware** | Correlation ID, request timing (`X-Process-Time`), CORS |
| **Container** | Multi-stage uv Dockerfile, layer caching, non-root user, healthcheck |
| **Quality gate** | `ruff`, `mypy --strict`, `pytest` + coverage, `pre-commit` — mirrored in CI |
| **Agent-ready** | `AGENTS.md`, `CLAUDE.md`, ADRs, vertical-slice recipes |

## Architecture

Layers with a single **inward-only** import direction — `api → services → ai → core`. HTTP lives in
`api/`, business logic in `services/` and `app/ai/`, cross-cutting infrastructure in `core/`.
Services and providers never import HTTP primitives; they raise `AppException` subclasses instead.

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
├── middleware/             # ASGI middleware (timing)
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

## AI primitives

**Provider seam** — `app/ai/providers.py` defines a `ChatProvider` Protocol with async `complete()`
and `stream()` plus a `name` (which feeds the cache key). `build_provider()` selects by
`AI_PROVIDER`; `get_provider()` is the cached singleton injected into endpoints.

**Echo provider** — the default `EchoChatProvider` echoes the last user message back, token by token.
Deterministic, no API key, no network — perfect for local dev, demos, and hermetic tests.

**Chat service** — `ChatService` orchestrates cache lookup/write and provider calls. The cache key
hashes provider name, model, `AI_PROMPT_VERSION`, temperature, and messages, so changing any of them
correctly misses the cache.

**Streaming** — built on Starlette's `StreamingResponse` (no extra dependency). The service yields
typed events — `start` → `token`\* → `done` (or a terminal `error` if a provider fails mid-stream) —
and the endpoint serializes them as SSE with `Cache-Control: no-store`.

**Cache tiers** — start simple, scale when you need to:

| Tier | Status | When |
|------|--------|------|
| In-process (TTL + LRU) | ✅ built-in default | single instance / dev / most starts |
| Redis (shared) | 🔌 documented seam | multiple workers/replicas need a shared cache |
| Semantic / vector | 🧭 future seam | dedupe near-duplicate prompts (out of scope for a starter) |

## Agent-first workflow

This template treats coding agents as first-class contributors.

- **[`AGENTS.md`](./AGENTS.md)** — the canonical contract: setup, the `make check` command contract,
  repo map, AI architecture, layer rules, vertical-slice recipes, streaming/caching/testing rules,
  the PR checklist, and Always/Ask-first/Never boundaries.
- **[`CLAUDE.md`](./CLAUDE.md)** — Claude Code operating notes that import and defer to `AGENTS.md`.
- **`.github/copilot-instructions.md`** — a concise mirror that points to the same source of truth.

**Ponytail-inspired rigor.** Adapted from the [Ponytail](https://skillsllm.com/skill/ponytail) skill:
lazy means *efficient, not careless*. Before writing code, agents climb a decision ladder
(does it need to exist? → reuse → stdlib → platform feature → installed dep → one line → minimum
viable) and never cut safety carve-outs (trust-boundary validation, security, data-loss prevention,
accessibility, typed errors). Intentional simplifications get a `ponytail:` comment naming the
upgrade path, and every task ends with a deletion-first review pass.

## Extending

Mirror the existing patterns — each extension is a small, predictable change.

**Add an endpoint (vertical slice)** — schema → service → endpoint → register → test. See the recipe
in [`AGENTS.md`](./AGENTS.md).

**Add a real LLM provider**
1. Implement `ChatProvider` in `app/ai/providers.py` with a **lazy-imported** SDK (add it as an
   opt-in optional dependency so the default install stays lean).
2. Wire it into `build_provider()` keyed on `settings.AI_PROVIDER`.
3. Add settings (e.g. `OPENAI_API_KEY: SecretStr | None`) to `Settings` and `.env.example`.
   Never require a key for the default `echo` path or for tests.

**Add a shared cache backend** — implement `CacheBackend` (e.g. Redis) and return it from
`build_cache()`; the rest of the app is unchanged.

**Other documented seams** — database (SQLAlchemy 2.0 + Alembic), auth (JWT), background tasks
(ARQ/Celery), rate limiting (slowapi), observability (OpenTelemetry). Each is intentionally *not*
pre-built; see [`docs/architecture.md`](./docs/architecture.md).

## Deployment

The **container is the portable contract** — the same image runs on any platform that runs
containers.

```bash
make docker-build
make docker-run        # serves on :8000 with your .env
```

Binds `$PORT` automatically (via `gunicorn.conf.py`, workers from `$WEB_CONCURRENCY`), exposes
health at `/api/v1/health/` and a dependency-checking readiness probe at `/api/v1/health/ready`, and
reads all config (and secrets) from the environment. In production `SECRET_KEY` must be overridden
or the app refuses to boot. A provider matrix for Cloud Run, AWS App Runner/ECS, Azure Container
Apps, Fly.io, Render, Railway, and DigitalOcean lives in [`docs/deployment.md`](./docs/deployment.md).

## Quality gates

```bash
make check        # lint + typecheck + test — the gate; must be green before "done"
make lint         # ruff check .
make format       # ruff format .
make typecheck    # mypy app/  (strict)
make test         # pytest -v
make test-cov     # pytest with coverage (terminal + HTML)
make precommit    # run all pre-commit hooks
```

The same checks run in GitHub Actions on every push and PR: `ruff` lint + format check,
`mypy --strict`, and `pytest` with coverage (floor enforced). `pre-commit` mirrors them locally.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/chat/` | Chat completion (cached) |
| `POST` | `/api/v1/chat/stream` | Streaming chat completion (SSE) |
| `GET` | `/api/v1/health/` | Liveness probe |
| `GET` | `/api/v1/health/ready` | Readiness probe |
| `GET` | `/api/v1/items/` | List items (example resource) |
| `POST` | `/api/v1/items/` | Create item |
| `GET` | `/api/v1/items/{id}` | Get item |
| `PATCH` | `/api/v1/items/{id}` | Update item |
| `DELETE` | `/api/v1/items/{id}` | Delete item |

Interactive docs at `/docs` (Swagger) and `/redoc` when `DEBUG=true`.

## Documentation

- [`AGENTS.md`](./AGENTS.md) — the canonical contributor & agent contract
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — how to land a change; [`SECURITY.md`](./SECURITY.md) — reporting vulnerabilities
- [`CLAUDE.md`](./CLAUDE.md) — Claude Code operating notes
- [`docs/architecture.md`](./docs/architecture.md) — module map, request lifecycle, invariants, seams
- [`docs/deployment.md`](./docs/deployment.md) — provider-neutral deployment guide
- [`docs/adr/0001-template-architecture.md`](./docs/adr/0001-template-architecture.md) — base architecture decisions
- [`docs/adr/0002-ai-application-building-blocks.md`](./docs/adr/0002-ai-application-building-blocks.md) — AI building-block decisions

## License

MIT © Zain Ghulam Zada
