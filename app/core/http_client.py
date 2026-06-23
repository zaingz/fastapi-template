from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.core.config import Settings


def build_async_client(settings: Settings) -> httpx.AsyncClient:
    """Construct the shared outbound client with explicit per-phase timeouts and pool limits.

    Created once in the lifespan and reused for all downstream calls so connections are
    pooled and a hung upstream is bounded by the read timeout rather than pinning a worker.
    """
    timeout = httpx.Timeout(
        connect=settings.HTTP_CONNECT_TIMEOUT,
        read=settings.HTTP_READ_TIMEOUT,
        write=settings.HTTP_WRITE_TIMEOUT,
        pool=settings.HTTP_POOL_TIMEOUT,
    )
    limits = httpx.Limits(
        max_connections=settings.HTTP_MAX_CONNECTIONS,
        max_keepalive_connections=settings.HTTP_MAX_KEEPALIVE_CONNECTIONS,
    )
    return httpx.AsyncClient(timeout=timeout, limits=limits)


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Inject the lifespan-managed shared client. Fails loudly if startup didn't run."""
    client: httpx.AsyncClient | None = getattr(request.app.state, "http_client", None)
    if client is None:
        raise RuntimeError(
            "HTTP client unavailable — lifespan did not initialize app.state.http_client"
        )
    return client


HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]
