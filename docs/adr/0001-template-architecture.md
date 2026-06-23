# 0001 — Template architecture

- Status: Accepted
- Date: 2026-06-23

## Context

This is a starter template meant to be cloned and extended, increasingly by coding agents as
well as humans. It must be small enough to read in one sitting, yet encode enough structure that
extensions land in predictable places and the quality gate stays trustworthy.

## Decision

1. **Layered, inward-only imports** — `api → services → core`. HTTP concerns live in
   `api/`, business logic in `services/`, cross-cutting infrastructure in `core/`. Services never
   import HTTP types and raise `AppException` subclasses instead of `HTTPException`.
2. **Application factory** — `create_application()` builds the app so tests and alternate entry
   points can construct isolated instances and override dependencies.
3. **Typed settings via pydantic-settings** — one `Settings` object, read through a cached
   `get_settings()` and injected with `Annotated` DI. No ad-hoc `os.environ` access.
4. **Uniform error contract** — all failures pass through `core/exception_handlers` and emit the
   same JSON shape, so clients (and agents writing them) get one error format.
5. **Structured logging** — structlog with correlation IDs; console renderer in dev, JSON in prod.
6. **Strict quality gate** — `ruff` + `mypy --strict` + `pytest` behind `make check`, mirrored in
   CI. A green gate is a precondition for any change.
7. **Minimal by default** — no database, auth, queue, or rate limiting until needed. Extension
   seams are marked (notably `lifespan.py`) rather than pre-built.

## Consequences

- New features follow a fixed vertical-slice recipe (schema → service → endpoint → router → test),
  which is easy for agents to follow and for reviewers to check.
- The layering rule is the most common thing to get wrong; it is enforced by review and called out
  in `AGENTS.md`, not by tooling.
- Keeping the template minimal means adopters add their own persistence/auth; the docs point to
  where each belongs.

## Agent rules derived from this decision

- Keep HTTP out of `services/`; raise `AppException` subclasses, never `HTTPException`, in services.
- Preserve the application-factory, `get_settings()`, and structlog patterns — do not bypass them.
- Add config only as typed `Settings` fields documented in `.env.example`.
- Every behavior change ships with tests; `make check` must pass before the work is done.
- Do not add heavy dependencies (DB, auth, queues) unless the task explicitly calls for them.
