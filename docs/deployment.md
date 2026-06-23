# Deployment

The **container is the portable contract**: the image built from the repo `Dockerfile` runs the
same way everywhere. Pick any platform that runs a container and you are done — there is no
platform-specific code in the app.

## The contract every platform must satisfy

- **Port** — the container binds `$PORT` (default `8000`) via `gunicorn.conf.py`, so platforms that
  inject `$PORT` (Cloud Run, Render, Railway, Heroku-likes) work with **no override needed**. The
  ASGI server owns the bind, not app config. Worker count comes from `$WEB_CONCURRENCY` (default 2).
- **Health** — liveness `GET /api/v1/health/`, readiness `GET /api/v1/health/ready`. Point the
  platform health check at the liveness path (the `Dockerfile` `HEALTHCHECK` already does locally).
  Readiness round-trips the cache and returns `503` if a dependency check fails — gate orchestrator
  routing on it, and add DB/Redis/provider pings there as you grow (see "Readiness checks" below).
- **Config** — everything is env-driven (see `.env.example`). Set `ENVIRONMENT=production`,
  `DEBUG=false`, `LOG_JSON=true` in real deployments.
- **Secrets** — provide via the platform's secret store as env vars (e.g. `SECRET_KEY`,
  `OPENAI_API_KEY`). Never bake secrets into the image or commit a real `.env`. `SECRET_KEY` **must**
  be overridden in production — the app refuses to boot on the shipped placeholder.
- **Default path is self-contained** — with `AI_PROVIDER=echo` the service needs no external API
  or datastore, so a bare container deploy works immediately.

## Local

```bash
docker compose up --build      # http://localhost:8000  (docs at /docs when DEBUG=true)
```

`docker-compose.yml` mounts source with watch/reload for local iteration.

## Provider matrix

| Platform | How | Notes |
|----------|-----|-------|
| **Google Cloud Run** | `gcloud run deploy --source .` | Injects `$PORT`; bind it. Scales to zero. |
| **AWS App Runner / ECS Fargate** | push image to ECR, point service at it | App Runner reads health path; Fargate needs an ALB health check. |
| **Azure Container Apps** | `az containerapp up --source .` | Set `--target-port 8000`, ingress external. |
| **Fly.io** | `fly launch` then `fly deploy` | `internal_port = 8000`; secrets via `fly secrets set`. |
| **Render** | new Web Service from repo (Docker) | Injects `$PORT`; health check path `/api/v1/health/`. |
| **Railway** | deploy from repo (Dockerfile) | Injects `$PORT`; set vars in the dashboard. |
| **DigitalOcean App Platform** | app spec → Dockerfile | HTTP port `8000`; health check on liveness path. |
| **Vercel** | not a fit for long-lived ASGI/SSE | Use a container platform above; Vercel functions don't suit streaming servers. |

## Scaling notes

- **Workers** — the image runs gunicorn with the maintained `uvicorn_worker.UvicornWorker`
  (`gunicorn.conf.py`). Set `WEB_CONCURRENCY` to size the pool to the instance's CPU (default 2);
  prefer horizontal replicas over many workers per tiny instance.
- **Cache across replicas** — the default AI cache is **in-process**, so each replica/worker has its
  own. That's fine for most starts. For a shared cache, add a Redis `CacheBackend`
  (`app/ai/cache.py`) as an opt-in dependency — see [`architecture.md`](architecture.md).
- **Provider timeout** — `AI_REQUEST_TIMEOUT` (seconds) caps each provider call/token so a hung
  upstream can't pin a worker; non-streaming overruns return `504`, streaming overruns emit a
  terminal `error` event.
- **Streaming** — SSE responses are `Cache-Control: no-store` and set `X-Accel-Buffering: no`.
  Ensure any reverse proxy/CDN in front does not buffer `text/event-stream`.

## Readiness checks

`GET /api/v1/health/ready` reports per-dependency status and returns `503` if any check fails.
Out of the box it round-trips the in-process cache (`{"cache": "ok"}`). As you add dependencies on
the request path, ping each one in `app/api/v1/endpoints/health.py` and include it in `checks`:

- **Database** — a `SELECT 1` against the pool.
- **Redis / shared cache** — a `PING`.
- **External provider** — a cheap, cached liveness call (avoid per-probe paid API calls).

Keep liveness (`/health/`) dependency-free — it must stay green while dependencies flap so the
orchestrator restarts only truly dead processes, and drains traffic (via readiness) from degraded
ones.
