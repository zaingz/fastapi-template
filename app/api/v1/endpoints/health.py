from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.ai.cache import CacheBackend, get_cache
from app.core.dependencies import SettingsDep

router = APIRouter()

CacheDep = Annotated[CacheBackend, Depends(get_cache)]


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Application health",
    description="Returns 200 if the application process is running.",
)
async def health(settings: SettingsDep) -> HealthResponse:
    """Liveness probe — is the process up?"""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


async def _check_cache(cache: CacheBackend) -> str:
    """Lightweight round trip through the configured cache backend."""
    probe_key = "__readiness__"
    await cache.set(probe_key, "1", ttl=5)
    return "ok" if await cache.get(probe_key) == "1" else "degraded"


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Application readiness",
    description="Returns 200 if dependencies are reachable, 503 otherwise.",
)
async def ready(cache: CacheDep, response: Response) -> ReadyResponse:
    """Readiness probe — are dependencies available?

    Checks every dependency on the request path and reports per-dependency status.
    When you add a DB/Redis/provider, add its ping here and gate readiness on it
    (return 503 if any check fails) so orchestrators stop routing to a broken pod.
    """
    checks = {"cache": await _check_cache(cache)}
    ok = all(status == "ok" for status in checks.values())
    if not ok:
        response.status_code = 503
    return ReadyResponse(status="ok" if ok else "degraded", checks=checks)
