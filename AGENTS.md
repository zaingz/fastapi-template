# AGENTS.md

Canonical briefing for coding agents (and humans) working in this repo. This is the single
source of truth; `CLAUDE.md` and `.github/copilot-instructions.md` point here.

This is a **minimal, production-shaped FastAPI template** meant to be cloned and extended.
Keep it lean: preserve the architecture, do not add frameworks or domain code speculatively.

## Setup

```bash
uv sync --all-groups      # install runtime + dev deps into .venv
cp .env.example .env       # local config (optional; sane defaults exist)
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
app/api/v1/           router.py → endpoints/ (HTTP) + schemas/ (Pydantic models)
app/services/         business logic (no HTTP)
tests/                async tests via httpx ASGITransport
docs/architecture.md  module map, request lifecycle, invariants, extension points
docs/adr/             architecture decision records
```

Imports flow **inward only**: `api → services → core`. `core` and `services` never import `api`.

## Layer rules (most important)

- **Endpoints** (`api/v1/endpoints/`) are HTTP-only: parse/validate input, call a service, return a
  `response_model`. No business logic.
- **Services** (`services/`) hold all business logic and contain **no HTTP primitives** — no
  `Request`/`Response`, no status codes, and **`HTTPException` is forbidden**. Signal failure by
  raising `AppException` subclasses (`NotFoundError`, `ConflictError`, …) from `core/exceptions.py`.
- **core/** is cross-cutting infrastructure only; it has no resource/business logic.
- Errors are rendered uniformly by `core/exception_handlers.py`; don't hand-build error JSON.

## Add an endpoint (vertical slice)

Mirror the `items` resource — schema → service → endpoint → register → test:

1. `app/api/v1/schemas/<name>.py` — Create/Update/Response/List Pydantic models.
2. `app/services/<name>.py` — `XService` class + `get_x_service()` DI factory; raise `AppException`s.
3. `app/api/v1/endpoints/<name>.py` — `APIRouter()` handlers with `response_model`, delegating to the service.
4. `app/api/v1/router.py` — import and `include_router(..., prefix="/<name>", tags=["..."])`.
5. `tests/api/v1/test_<name>.py` — async tests for success and error paths.

## Testing rules

- `asyncio_mode = "auto"`: write `async def test_...`, no decorator.
- Use the `async_client` fixture (real ASGI app, no live server). Override behavior via
  `app.dependency_overrides`, not monkeypatching or framework mocks.
- Reset stateful stores between tests with an autouse fixture (see `conftest.py`).
- Assert on status code **and** body, including the `error` code for failures.
- Every behavior change ships with a test in the same PR.

## Config & dependencies

- Settings only via `get_settings()` / `SettingsDep` — never `os.environ`. Each new setting is a
  typed `Settings` field **and** an entry in `.env.example`. Secrets use `SecretStr`.
- Add deps with `uv add <pkg>` / `uv add --dev <pkg>`; commit the updated `uv.lock`. Never hand-edit it.
- Keep `mypy --strict` clean: parameterize generics (`dict[str, Any]`, not `dict`); type public functions.

## Always / Ask first / Never

**Always**
- Run `make check` green before finishing.
- Add/update tests for behavior changes; update `.env.example` for new settings.
- Update `AGENTS.md` + `docs/` when you change a convention or add a layer.
- Match existing patterns (app factory, Annotated DI, structlog key/values, uniform errors).

**Ask first**
- Adding heavy dependencies or subsystems (database, auth, queue, cache, rate limiting).
- Introducing a new top-level package or changing the layer boundaries.
- Creating a new API version (`api/vN`) or making breaking changes to `/api/v1`.
- Changing tooling/CI/quality-gate config or relaxing `ruff`/`mypy` strictness.

**Never**
- Put business logic in endpoints or HTTP primitives (incl. `HTTPException`) in services.
- Read env vars directly, hand-edit `uv.lock`, or log/serialize raw secret values.
- Weaken or skip the quality gate (`# type: ignore`, `# noqa`, `--no-verify`) to make it pass.
- Commit secrets or a real `.env`.

## Reference

- Architecture details: [`docs/architecture.md`](docs/architecture.md)
- Decisions & rationale: [`docs/adr/0001-template-architecture.md`](docs/adr/0001-template-architecture.md)
