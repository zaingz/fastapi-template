# syntax=docker/dockerfile:1.9
# ── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Install dependencies only (cached until uv.lock changes)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy source and install the project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm

RUN groupadd -r app && useradd -r -d /app -g app -s /sbin/nologin app

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app
WORKDIR /app

# Platforms that inject $PORT (Cloud Run, Render, Railway, Fly) override this at runtime;
# gunicorn.conf.py binds $PORT (default 8000). EXPOSE is documentation only.
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f\"http://localhost:{os.environ.get('PORT','8000')}/api/v1/health/\")"

# Bind/workers come from gunicorn.conf.py (reads $PORT and $WEB_CONCURRENCY).
CMD ["gunicorn", "app.main:app", "--config", "gunicorn.conf.py"]
