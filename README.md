# FastAPI Template

A lean, **batteries-included FastAPI starter for AI applications**. Clone it and you have a chat
API with streaming and caching running on a built-in `echo` provider — **no API key, no network,
no external services** — plus a clearly marked seam to drop in a real LLM provider.

## Features

- **AI domain out of the box** — `POST /api/v1/chat` (cached) and `POST /api/v1/chat/stream` (SSE),
  a `ChatProvider` seam (default `EchoChatProvider`), and a TTL+LRU response cache
- **FastAPI** with application factory pattern and async lifespan management
- **pydantic-settings** for type-safe configuration from environment variables
- **structlog** for structured, request-correlated JSON logging
- **Annotated-type dependency injection** throughout
- **Custom exception hierarchy** with consistent JSON error responses
- **Middleware stack**: correlation ID, request timing, CORS
- **URL-based API versioning** (`/api/v1/`)
- **Docker** multi-stage build with uv, layer caching, non-root user
- **pytest + httpx** async testing scaffold
- **Ruff** for linting and formatting
- **mypy** for strict type checking
- **GitHub Actions** CI pipeline

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Setup

```bash
# Clone
git clone https://github.com/zaingz/fastapi-template.git
cd fastapi-template

# Install dependencies
uv sync

# Copy environment file
cp .env.example .env

# Run development server
make dev
```

The API is available at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs` (when DEBUG=true).

### Try the chat API (no API key needed)

```bash
# Non-streaming (cached) — runs on the built-in echo provider
curl -s localhost:8000/api/v1/chat/ \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"hello world"}]}'

# Streaming (Server-Sent Events): start → token* → done
curl -N localhost:8000/api/v1/chat/stream \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"stream this"}]}'
```

To use a real model instead of `echo`, add a `ChatProvider` in `app/ai/providers.py` (lazy-imported
SDK behind an opt-in extra) and set `AI_PROVIDER` — see [`docs/architecture.md`](./docs/architecture.md).

### Running Tests

```bash
make test
```

### Docker

```bash
make docker-build
make docker-run
```

## Project Structure

```
app/
├── main.py                 # Application factory
├── core/                   # Cross-cutting infrastructure
│   ├── config.py           # Settings (pydantic-settings)
│   ├── dependencies.py     # Shared DI type aliases
│   ├── exceptions.py       # Exception hierarchy
│   ├── exception_handlers.py
│   ├── lifespan.py         # Startup/shutdown lifecycle
│   └── logging.py          # structlog configuration
├── middleware/              # ASGI middleware
│   └── timing.py           # X-Process-Time header
├── api/
│   └── v1/
│       ├── router.py       # v1 router aggregator
│       ├── schemas/        # Pydantic request/response models
│       └── endpoints/      # Route handlers (incl. chat)
├── ai/                     # AI domain: providers, cache, chat service
└── services/               # Non-AI business logic layer
```

## Extending

This template is designed to be extended. See the [Architecture](./docs/architecture.md) doc for
the AI provider seam and cache tiers, and [`docs/deployment.md`](./docs/deployment.md) for
provider-neutral deployment. Other documented seams:

- **Real LLM provider**: implement `ChatProvider` (lazy-imported SDK, opt-in extra)
- **Shared cache**: add a Redis `CacheBackend` for multi-instance deployments
- **Database**: Add SQLAlchemy 2.0 async + Alembic
- **Authentication**: Add JWT with python-jose
- **Background Tasks**: Add ARQ or Celery
- **Rate Limiting**: Add slowapi
- **Observability**: Add OpenTelemetry

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health/` | Liveness probe |
| GET | `/api/v1/health/ready` | Readiness probe |
| POST | `/api/v1/chat/` | Chat completion (cached) |
| POST | `/api/v1/chat/stream` | Streaming chat completion (SSE) |
| GET | `/api/v1/items/` | List items |
| POST | `/api/v1/items/` | Create item |
| GET | `/api/v1/items/{id}` | Get item |
| PATCH | `/api/v1/items/{id}` | Update item |
| DELETE | `/api/v1/items/{id}` | Delete item |

## Contributing & AI agents

Conventions, layer rules, and the workflow contract live in [`AGENTS.md`](./AGENTS.md) (the
canonical briefing for both humans and coding agents). Run `make check` before opening a PR.

## License

MIT
