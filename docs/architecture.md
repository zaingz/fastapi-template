# Architecture

Practical reference for humans and coding agents working in this template. For the
day-to-day workflow contract (commands, rules, boundaries) see [`AGENTS.md`](../AGENTS.md).

## Module map

```
app/
├── main.py                      # create_application() factory + module-level `app`
├── core/                        # cross-cutting infrastructure (no business logic)
│   ├── config.py                # Settings (pydantic-settings) + get_settings() singleton
│   ├── dependencies.py          # shared Annotated DI aliases (SettingsDep)
│   ├── exceptions.py            # AppException hierarchy (status_code + code + message)
│   ├── exception_handlers.py    # maps exceptions → uniform JSON error body
│   ├── lifespan.py              # async startup/shutdown; resource init/teardown
│   └── logging.py               # structlog configuration (console or JSON)
├── middleware/                  # ASGI middleware
│   └── timing.py                # X-Process-Time header
├── ai/                          # AI domain (business logic, no HTTP primitives)
│   ├── schemas.py               # ChatMessage/Request/Response + ChatStreamEvent
│   ├── providers.py             # ChatProvider Protocol + EchoChatProvider + build/get_provider
│   ├── cache.py                 # CacheBackend Protocol + InMemoryTTLCache + get_cache
│   └── service.py               # ChatService: cache lookup/write + provider calls
├── api/v1/                      # versioned HTTP surface
│   ├── router.py                # aggregates endpoint routers under /v1
│   ├── endpoints/               # route handlers (HTTP only; chat.py wires AI DI)
│   └── schemas/                 # Pydantic request/response models
└── services/                    # non-AI business logic (no HTTP primitives)
```

The single import direction is **inward**: `api → services → ai → core`. `core` never imports
outward; `ai` may import `core`. Nothing imports from `main` except the ASGI server.

## AI request lifecycle

Non-streaming `POST /api/v1/chat`:

1. The endpoint validates `ChatRequest` (message count + per-message length are trust-boundary caps).
2. `get_chat_service` injects the singleton `ChatProvider` and `CacheBackend` and builds `ChatService`.
3. `ChatService` computes a cache key over provider, model, `AI_PROMPT_VERSION`, temperature, and
   messages. On hit it returns `cached=True`; on miss it calls `provider.complete()`, stores, returns.

Streaming `POST /api/v1/chat/stream`:

1. Same validation and DI.
2. `ChatService.stream()` yields typed `ChatStreamEvent`s: `start` → `token`* → `done` (or a
   terminal `error` if the provider raises — exceptions never escape mid-stream).
3. The endpoint serializes each event to an SSE frame via `StreamingResponse`
   (`text/event-stream`, `Cache-Control: no-store`, `X-Accel-Buffering: no`). Streams are not cached.

### Provider seam

`ChatProvider` is a `Protocol` (async `complete`/`stream`, plus a `name` used in the cache key).
`EchoChatProvider` is the zero-dependency default — no API key, no network. `build_provider()`
selects by `AI_PROVIDER`; `get_provider()` is the cached singleton. To add a real provider, implement
the Protocol with a **lazy-imported** SDK behind an opt-in optional dependency and wire it into
`build_provider()` — never put a key or SDK on the default path.

### Caching tiers

1. **In-process** — `InMemoryTTLCache` (TTL + LRU, stdlib), the default singleton via `get_cache()`.
   Per-replica/per-worker.
2. **Shared (Redis)** — implement `CacheBackend` against Redis as an opt-in dependency for
   multi-instance deployments. Documented seam; not bundled.
3. **Semantic/vector** — out of scope for the starter; left as a future seam.

## Request lifecycle

1. **CorrelationIdMiddleware** assigns/propagates `X-Request-ID` (bound into every log line).
2. **TimingMiddleware** records wall time, sets `X-Process-Time` on the response.
3. **CORSMiddleware** applies origin policy.
4. Router dispatches to the matching `api/v1/endpoints` handler.
5. The handler resolves dependencies (`SettingsDep`, `ItemServiceDep`) and delegates to a service.
6. The service runs business logic and raises `AppException` subclasses on failure.
7. `exception_handlers` convert any error into the uniform body below; structlog emits the log.

Middleware is registered in `main.py` in reverse execution order (last added runs outermost).

### Uniform error body

Every error response (handled or unhandled) is shaped by `_error_body`:

```json
{
  "error": "NOT_FOUND",
  "message": "Item 'abc' not found",
  "details": {},
  "timestamp": "2026-06-23T12:00:00+00:00",
  "path": "/api/v1/items/abc"
}
```

## Invariants

- **Layering**: endpoints hold no business logic; services hold no HTTP types (no `Request`,
  `Response`, `HTTPException`, status codes). Services raise `AppException` subclasses only.
- **Config**: read settings via `get_settings()` / `SettingsDep`, never `os.environ`. Every new
  setting is a typed field on `Settings` and is documented in `.env.example`.
- **DI**: dependencies are `Annotated[T, Depends(...)]` aliases. Tests swap behavior through
  `app.dependency_overrides`, not monkeypatching.
- **Versioning**: breaking HTTP changes go in a new `api/vN`; `/api/v1` stays stable.
- **Typing**: `mypy --strict` must pass — no bare generics, no untyped public functions.
- **Logging**: use `structlog.get_logger(__name__)` with key/value pairs, not f-strings.

## Adding a new endpoint (vertical slice)

Mirror the `items` resource. To add resource `widgets`:

1. **Schemas** — `app/api/v1/schemas/widgets.py`: `WidgetCreate`, `WidgetUpdate`,
   `WidgetResponse`, `WidgetList` (Pydantic models with `Field` constraints).
2. **Service** — `app/services/widgets.py`: a `WidgetService` class with pure business logic
   plus a `get_widget_service()` factory for DI. Raise `NotFoundError(...)` etc.
3. **Endpoint** — `app/api/v1/endpoints/widgets.py`: a `router = APIRouter()` with handlers that
   declare `response_model`, accept `WidgetServiceDep`, and delegate to the service.
4. **Register** — add `widgets` to the imports and `include_router(...)` call in
   `app/api/v1/router.py` with `prefix="/widgets"` and `tags=["Widgets"]`.
5. **Test** — `tests/api/v1/test_widgets.py`: async tests via the `async_client` fixture covering
   success and error paths (at minimum: create, get, get-404).

## Testing strategy

- Tests run against the real ASGI app through `httpx.ASGITransport` (no live server, no mocks of
  the framework). Settings are overridden via `dependency_overrides` in `conftest.py`.
- `asyncio_mode = "auto"` — write `async def test_...` directly, no decorator needed.
- Stateful stores (e.g. the in-memory `_ITEMS`) are reset by an autouse fixture between tests.
- Assert on both status code and the JSON body, including the `error` code on failures.
- Run with coverage: `make test-cov` (project currently ~89%; CI floor is 80%).

## Configuration & dependency policy

- Add runtime deps with `uv add <pkg>`, dev deps with `uv add --dev <pkg>`; commit the updated
  `uv.lock`. Never hand-edit `uv.lock`.
- New env vars: typed field on `Settings` → entry in `.env.example` → consumed via DI.
- Secrets use `SecretStr`; never log or serialize their raw value.

## Extension points (intentionally not pre-built)

The template stays minimal. When the application needs them, wire these in at the marked seams:

- **Database** — SQLAlchemy 2.0 async engine + Alembic. Init the engine in `lifespan.py`
  (`app.state.db_engine`), expose an `AsyncSession` DI alias, replace the in-memory store in a
  service with a repository.
- **Auth** — JWT dependency in `core/`, surfaced as an `Annotated` current-user alias; add
  `UnauthorizedError` (401) / `ForbiddenError` (403) `AppException` subclasses in `core/exceptions.py`.
- **Background tasks** — ARQ or Celery; start/stop the worker client in `lifespan.py`.
- **Rate limiting** — slowapi middleware; add a `RateLimitError` (429) `AppException` subclass.
- **Observability** — OpenTelemetry instrumentation alongside the structlog setup.

See [`docs/adr/0001-template-architecture.md`](./adr/0001-template-architecture.md) for the
rationale behind these decisions.
