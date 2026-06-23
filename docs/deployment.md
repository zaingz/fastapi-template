# Deployment

The **container is the portable contract**: the image built from the repo `Dockerfile` runs the
same way everywhere. Pick any platform that runs a container and you are done — there is no
platform-specific code in the app.

## The contract every platform must satisfy

- **Port** — the app listens on `8000`. Platforms that inject `$PORT` (Cloud Run, Render, Railway,
  Heroku-likes) expect the process to bind it. Override the bind at deploy time, e.g.
  `gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT`.
- **Health** — liveness `GET /api/v1/health/`, readiness `GET /api/v1/health/ready`. Point the
  platform health check at the liveness path (the `Dockerfile` `HEALTHCHECK` already does locally).
- **Config** — everything is env-driven (see `.env.example`). Set `ENVIRONMENT=production`,
  `DEBUG=false`, `LOG_JSON=true` in real deployments.
- **Secrets** — provide via the platform's secret store as env vars (e.g. `SECRET_KEY`,
  `OPENAI_API_KEY`). Never bake secrets into the image or commit a real `.env`.
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

- **Workers** — the image runs gunicorn with uvicorn workers. Tune `--workers` to the instance's
  CPU; prefer horizontal replicas over many workers per tiny instance.
- **Cache across replicas** — the default AI cache is **in-process**, so each replica/worker has its
  own. That's fine for most starts. For a shared cache, add a Redis `CacheBackend`
  (`app/ai/cache.py`) as an opt-in dependency — see [`architecture.md`](architecture.md).
- **Streaming** — SSE responses are `Cache-Control: no-store` and set `X-Accel-Buffering: no`.
  Ensure any reverse proxy/CDN in front does not buffer `text/event-stream`.
