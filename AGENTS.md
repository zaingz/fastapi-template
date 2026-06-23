# AGENTS.md

Canonical briefing for coding agents (and humans) working in this repo. This is the single
source of truth; `CLAUDE.md` and `.github/copilot-instructions.md` point here.

This is a **batteries-included, production-shaped FastAPI template for AI applications**. It works
the moment you clone it — a chat domain with streaming and caching runs on a built-in `echo`
provider with **no API key and no network**. Real providers are a documented seam, not bundled.
Keep it lean: add core building blocks, not frameworks or speculative complexity.

## Working philosophy (adapted from Ponytail)

> Adapted from the [Ponytail](https://skillsllm.com/skill/ponytail) skill. Lazy means *efficient,
> not careless*: the best code is the code you don't write.

**Before writing code, climb the ladder — stop at the first rung that works:**

1. **Does it need to exist?** If not, skip it (YAGNI). Deletion beats addition.
2. **Already in this codebase?** Reuse it.
3. **Standard library?** Use it.
4. **Native platform / framework feature?** (Starlette `StreamingResponse`, Pydantic validation,
   FastAPI DI) — use it before adding code.
5. **Already-installed dependency?** Use it before adding a new one.
6. **Expressible in one line?** Write the one line.
7. **Only then** write the minimum viable code.

**Never-cut safety carve-outs.** Laziness applies to *solutions*, never to correctness. Never
trim: trust-boundary validation (request size/shape limits), security (secret handling, authz),
data-loss prevention, accessibility, typed errors (`AppException` + uniform body), or behavior the
task explicitly asked for. When in doubt, keep the guard and defer the feature.

**`ponytail:` comment convention.** When you intentionally simplify, leave one line naming the
known ceiling and the upgrade path — so the next reader (human or agent) sees the seam:

```python
# ponytail: in-process cache only; add a Redis backend (CacheBackend) for multi-instance. See docs/architecture.md.
```

**Deletion-first review pass.** Before declaring a task done, briefly list what you *removed or
chose not to add* and why. Fewer moving parts is the goal; justify every new file and dependency.

## Communication style (Caveman)

Terse prose, exact technical substance. Drop filler, pleasantries, hedging, and repeated
explanations. Preserve code, commands, URLs, file paths, headings, dates, and version numbers
verbatim. Status pattern: *what changed → why → how verified → next step.* Code, commits, and PR
text stay in normal professional style — Caveman applies to chat/status prose, not artifacts.

## Setup

```bash
uv sync --all-groups       # install runtime + dev deps into .venv
cp .env.example .env        # local config (optional; sane defaults exist)
```

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/). Use `uv run <cmd>` or `make`.

## Commands (the contract)

| Task        | Command          | Notes                                            |
|-------------|------------------|--------------------------------------------------|
| Dev server  | `make dev`       | uvicorn reload on :8000; docs at `/docs`         |
| Lint        | `make lint`      | `ruff check .`                                    |
| Format      | `make format`    | `ruff format .`                                   |
| Type check  | `make typecheck` | `mypy app/` (strict)                              |
| Test        | `make test`      | `pytest -v`                                        |
| Coverage    | `make test-cov`  | terminal + HTML report                            |
| **Gate**    | **`make check`** | **lint + typecheck + test — must pass before done** |

**Always run `make check` and confirm it is green before declaring a task complete.**

## Repo map

```
app/main.py           create_application() factory + module-level `app`
app/core/             config, dependencies, exceptions, exception_handlers, lifespan, logging
app/middleware/       ASGI middleware (timing)
app/ai/               AI domain: schemas, providers (echo + seam), cache, service
app/api/v1/           router.py → endpoints/ (HTTP) + schemas/ (Pydantic models)
app/services/         non-AI business logic (no HTTP)
tests/                async tests via httpx ASGITransport
docs/architecture.md  module map, request lifecycle (incl. AI), invariants, extension points
docs/deployment.md    provider-neutral container deployment guide
docs/adr/             architecture decision records
```

Imports flow **inward only**: `api → services → ai → core`. `core` never imports outward; `ai`
may import `core`; nothing imports from `main` except the ASGI server.

## Layer rules (most important)

- **Endpoints** (`api/v1/endpoints/`) are HTTP-only: parse/validate input, call a service, return a
  `response_model` (or a `StreamingResponse` for SSE). No business logic.
- **Services** (`services/`, `app/ai/service.py`) hold all business logic and contain **no HTTP
  primitives** — no `Request`/`Response`, no status codes, and **`HTTPException` is forbidden**.
  Signal failure by raising `AppException` subclasses from `core/exceptions.py`.
- **`app/ai/`** is the AI domain: provider seam, cache, and orchestration. Providers are HTTP-
  agnostic and async; the service is the only place provider + cache are combined.
- **core/** is cross-cutting infrastructure only; no resource/business logic.
- Errors are rendered uniformly by `core/exception_handlers.py`; don't hand-build error JSON.
- **Routing convention** — the app sets `redirect_slashes=False`. Define and call endpoints with
  their **trailing slash** (`/api/v1/chat/`, `/api/v1/items/`); a missing/extra slash 404s instead
  of redirecting. Sub-paths like `/chat/stream` have no trailing slash.

## AI architecture (the building blocks)

- **Provider seam** (`app/ai/providers.py`) — `ChatProvider` Protocol with async `complete()` and
  `stream()`. `EchoChatProvider` is the zero-dependency default. `build_provider(settings)` selects
  by `AI_PROVIDER`; `get_provider()` is the cached singleton injected via DI.
- **Cache** (`app/ai/cache.py`) — `CacheBackend` Protocol; `InMemoryTTLCache` (TTL + LRU, stdlib)
  is the default singleton via `get_cache()`. Redis is a documented seam, not bundled.
- **Service** (`app/ai/service.py`) — `ChatService` does cache lookup/write and provider calls. The
  cache key includes provider name, model, `AI_PROMPT_VERSION`, temperature, and messages.
- **Endpoints** (`app/api/v1/endpoints/chat.py`) — `POST /api/v1/chat` (cached, non-streaming) and
  `POST /api/v1/chat/stream` (SSE).

### Add or swap an AI provider

1. Add a class in `app/ai/providers.py` implementing `ChatProvider` (`name`, async `complete`,
   async `stream`). **Lazy-import** the SDK inside the class so the default path stays dependency-
   free; add the dep as an opt-in extra (`uv add --optional <group> <pkg>`).
2. Wire it into `build_provider()` keyed on `settings.AI_PROVIDER`.
3. Add any settings (e.g. `OPENAI_API_KEY: SecretStr | None`) to `Settings` and `.env.example`.
   **Never require a key for the default `echo` path or for tests.**

## Add an endpoint (vertical slice)

Mirror the `items` resource — schema → service → endpoint → register → test:

1. `app/api/v1/schemas/<name>.py` — Create/Update/Response/List Pydantic models.
2. `app/services/<name>.py` — `XService` class + `get_x_service()` DI factory; raise `AppException`s.
3. `app/api/v1/endpoints/<name>.py` — `APIRouter()` handlers with `response_model`, delegating to the service.
4. `app/api/v1/router.py` — import and `include_router(..., prefix="/<name>", tags=["..."])`.
5. `tests/api/v1/test_<name>.py` — async tests for success and error paths.

## Streaming rules

- Use Starlette `StreamingResponse` with `media_type="text/event-stream"`. Do **not** add
  `sse-starlette` — the built-in response is sufficient.
- The service yields typed `ChatStreamEvent`s; the endpoint only serializes them to SSE frames.
  Emit `start` → `token`* → `done`, and `error` as a terminal event if the provider fails (never
  let an exception escape mid-stream).
- Set `Cache-Control: no-store` and `X-Accel-Buffering: no`. **Streams are never cached.**

## Caching rules

- Cache **non-streaming** completions only. The key must contain everything that changes output
  (provider, model, prompt version, temperature, messages) — see `ChatService._cache_key`.
- Bump `AI_PROMPT_VERSION` when prompt construction changes, to invalidate stale entries.
- Default is in-process (`InMemoryTTLCache`). Need a shared cache across workers/instances? Add a
  Redis `CacheBackend` (opt-in extra, lazy import) — don't reach for it by default.
- Cache tiers, in order of reach: in-process → Redis (shared) → semantic/vector (future, not built).

## Testing rules

- `asyncio_mode = "auto"`: write `async def test_...`, no decorator.
- Use the `async_client` fixture (real ASGI app, no live server). Override behavior via
  `app.dependency_overrides`, not monkeypatching or framework mocks.
- Reset stateful stores between tests with an autouse fixture (see `conftest.py`: `clear_items`,
  `clear_cache`).
- Assert on status code **and** body, including the `error` code for failures. For streams, assert
  on the emitted event sequence.
- **Streaming changes must test a provider failure → terminal `event: error`** (never a leaked
  exception mid-stream). Use a test-only failing provider via `app.dependency_overrides[get_provider]`
  — see `tests/ai/test_chat_reliability.py`.
- To assert the uniform 500 body through the client, build an `ASGITransport(app, raise_app_exceptions=False)`
  so the registered handler's body reaches the client (mirrors a real ASGI server).
- Every behavior change ships with a test in the same PR.

## Config & dependencies

- Settings only via `get_settings()` / `SettingsDep` — never `os.environ`. Each new setting is a
  typed `Settings` field **and** an entry in `.env.example`. Secrets use `SecretStr`.
- Add deps with `uv add <pkg>` / `uv add --dev <pkg>`; commit the updated `uv.lock`. Never hand-edit it.
  Provider SDKs and Redis go in **opt-in optional groups**, lazy-imported — never on the default path.
- Keep `mypy --strict` clean: parameterize generics (`dict[str, Any]`, not `dict`); type public functions.

## Deployment

- The container is the portable contract; the same image runs anywhere. See
  [`docs/deployment.md`](docs/deployment.md).
- The ASGI server owns the network bind, not app `Settings`. `gunicorn.conf.py` reads `$PORT`
  (default 8000) and `$WEB_CONCURRENCY` (workers) and uses the maintained `uvicorn_worker.UvicornWorker`.
  Platforms that inject `$PORT` work out of the box.
- Expose health at `/api/v1/health/` and readiness at `/api/v1/health/ready`. Provide secrets via
  environment, never baked into the image. `SECRET_KEY` must be overridden when
  `ENVIRONMENT=production` or the app refuses to boot.

## Always / Ask first / Never

**Always**
- Run `make check` green before finishing; keep the default path key-free and offline.
- Add/update tests for behavior changes; update `.env.example` for new settings.
- Update `AGENTS.md` + `docs/` when you change a convention or add a layer.
- Do a deletion-first pass; leave a `ponytail:` note at any intentional simplification.
- Match existing patterns (app factory, Annotated DI, structlog key/values, uniform errors).

**Ask first**
- Adding heavy dependencies or subsystems (real LLM SDK on the default path, database, auth, queue,
  Redis, rate limiting, vector DB/RAG, eval harness).
- Introducing a new top-level package or changing the layer boundaries.
- Creating a new API version (`api/vN`) or making breaking changes to `/api/v1`.
- Changing tooling/CI/quality-gate config or relaxing `ruff`/`mypy` strictness.

**Never**
- Put business logic in endpoints or HTTP primitives (incl. `HTTPException`) in services.
- Require an API key or network for the default provider or for tests.
- Cache streaming responses; let an exception escape mid-stream.
- Read env vars directly, hand-edit `uv.lock`, or log/serialize raw secret values.
- Weaken or skip the quality gate (`# type: ignore`, `# noqa`, `--no-verify`) to make it pass.
- Cut a never-cut safety carve-out for brevity. Commit secrets or a real `.env`.

## PR checklist

- [ ] `make check` green (lint + `mypy --strict` + tests); coverage floor holds.
- [ ] Tests added/updated for the behavior change (incl. stream event sequence if relevant).
- [ ] New settings are typed on `Settings` **and** in `.env.example`; secrets are `SecretStr`.
- [ ] Default path still runs with no API key and no network.
- [ ] Docs updated (`AGENTS.md` / `docs/`) if a convention or layer changed.
- [ ] Deletion-first note: what was removed/avoided, and any `ponytail:` seams left behind.

## Reference

- Architecture details: [`docs/architecture.md`](docs/architecture.md)
- Deployment: [`docs/deployment.md`](docs/deployment.md)
- Decisions & rationale: [`docs/adr/`](docs/adr/)
