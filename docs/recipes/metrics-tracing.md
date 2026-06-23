# Metrics & tracing

Observability instrumentation is opt-in. The template already emits structured access logs with
`request_id` (`app/middleware/access_log.py`); metrics and traces layer on top.

## Prometheus metrics

```bash
uv add --optional metrics prometheus-fastapi-instrumentator
uv sync --extra metrics
```

In `create_application()` (after routers), lazy-import and expose `/metrics`:

```python
if settings.METRICS_ENABLED:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(application).expose(application, endpoint="/metrics")
```

Add `METRICS_ENABLED: bool = False` to `Settings`. Scrape `/metrics` from Prometheus; default
metrics include request count, latency histogram, and in-progress requests per route.

## OpenTelemetry tracing

```bash
uv add --optional otel \
  opentelemetry-distro opentelemetry-exporter-otlp \
  opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx
```

Two ways to wire it:

- **Zero-code** — run under the agent: `opentelemetry-instrument uvicorn app.main:app` (or in
  `gunicorn.conf.py`). Configure via `OTEL_*` env vars (`OTEL_EXPORTER_OTLP_ENDPOINT`,
  `OTEL_SERVICE_NAME`).
- **Explicit** — in the lifespan, instrument the app and the shared client:

  ```python
  from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
  from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

  FastAPIInstrumentor.instrument_app(app)
  HTTPXClientInstrumentor().instrument()   # traces downstream calls via the shared client
  ```

Bind the OTel trace/span id into structlog (a processor that reads the current span context) so logs
and traces correlate alongside `request_id`. Keep instrumentation behind a setting so the default
path adds no overhead and no exporter dependency.
