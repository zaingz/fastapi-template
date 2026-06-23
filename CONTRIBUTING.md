# Contributing

Thanks for improving this template. It is read by humans **and** coding agents, so the bar is
"small, safe, verifiable changes."

## Read first

[`AGENTS.md`](./AGENTS.md) is the canonical contract — setup, the command contract, repo map,
layer rules, the vertical-slice recipe, and the Always/Ask-first/Never boundaries. This file is the
short version of *how to land a change*.

## Setup

```bash
uv sync --all-groups       # runtime + dev deps
cp .env.example .env        # optional; sane defaults exist
make dev                    # http://localhost:8000  (docs at /docs)
```

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

## The gate

`make check` (ruff lint + `ruff format --check` + `mypy --strict` + `pytest` with a coverage floor)
must be green before you open a PR. CI runs the same checks.

```bash
make check
```

Do **not** silence the gate with `# type: ignore`, `# noqa`, or `--no-verify`. Fix the cause.

## Working philosophy

- **Ponytail — lazy, not negligent.** Before adding code, climb the ladder: does it need to exist?
  stdlib? a native FastAPI/Pydantic/Python feature? an already-installed dependency? one line?
  otherwise the minimum clear implementation. Deletion beats addition. Leave a `ponytail:` comment
  at any intentional simplification, naming the upgrade path. **Never** cut validation, error
  handling, security, accessibility, trust-boundary checks, or data-loss handling. If config, an
  abstraction, or docs are unused — wire them or delete them.
- **Match existing patterns.** App factory, `Annotated` DI, structlog key/values, uniform
  `AppException` errors. Keep HTTP out of services; raise `AppException`, never `HTTPException`.

## Pull requests

- One focused change per PR. Every behavior change ships with a test in the same PR.
- Streaming changes must test a provider failure → terminal `event: error` (never a leaked
  exception mid-stream).
- New settings are a typed `Settings` field **and** an `.env.example` entry; secrets use `SecretStr`.
- Update `AGENTS.md` / `docs/` when you change a convention or add a layer.
- Keep the default path key-free and offline (the `echo` provider and in-process cache).
- Fill in the PR template, including the AI-agent disclosure line.

## Reporting bugs / requesting features

Use the issue templates under `.github/ISSUE_TEMPLATE/`. For security issues, **do not** open a
public issue — see [`SECURITY.md`](./SECURITY.md).
