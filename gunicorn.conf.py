"""Gunicorn config for the container entrypoint.

The ASGI server owns the network bind, not app `Settings` — so binding stays correct no
matter how the platform launches the image. Everything here is env-driven:

- ``PORT`` — platforms like Cloud Run / Render / Railway / Fly inject it; default 8000.
- ``WEB_CONCURRENCY`` — worker count (gunicorn's native env var); default 2.

ponytail: no custom logging/timeout knobs until a deployment needs them — gunicorn's
defaults are sane. Override any setting at deploy time via ``GUNICORN_CMD_ARGS`` or env.
"""

import os

# Bind every interface on the platform-provided port (or 8000 locally).
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Uvicorn's maintained worker class (the in-tree uvicorn.workers shim is deprecated).
worker_class = "uvicorn_worker.UvicornWorker"

# Honor WEB_CONCURRENCY if set; otherwise a small, safe default. Prefer horizontal
# replicas over many workers on a tiny instance.
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))

# Stream logs to stdout/stderr for container log collectors.
accesslog = "-"
errorlog = "-"
