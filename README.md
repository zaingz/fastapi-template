# FastAPI Template

A minimal, production-ready FastAPI starter template with modern Python patterns.

## Features

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
│       └── endpoints/      # Route handlers
└── services/               # Business logic layer
```

## Extending

This template is designed to be extended. See the [Architecture Report](./docs/architecture.md) for detailed extension guides:

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
| GET | `/api/v1/items/` | List items |
| POST | `/api/v1/items/` | Create item |
| GET | `/api/v1/items/{id}` | Get item |
| PATCH | `/api/v1/items/{id}` | Update item |
| DELETE | `/api/v1/items/{id}` | Delete item |

## License

MIT
