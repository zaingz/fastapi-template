from fastapi import APIRouter
from pydantic import BaseModel

from app.core.dependencies import SettingsDep

router = APIRouter()


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


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Application readiness",
    description="Returns 200 if the application is ready to serve traffic.",
)
async def ready() -> ReadyResponse:
    """Readiness probe — are dependencies available?

    Extension point: add database ping, cache ping, etc.
    """
    return ReadyResponse(
        status="ok",
        checks={},
    )
