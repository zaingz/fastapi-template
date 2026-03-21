from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import v1_router
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.lifespan import lifespan
from app.middleware.timing import TimingMiddleware


def create_application() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance."""
    settings = get_settings()

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        redirect_slashes=False,
    )

    # Middleware — registered in reverse execution order
    # Last added = outermost (runs first on request, last on response)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )
    application.add_middleware(TimingMiddleware)
    application.add_middleware(CorrelationIdMiddleware)

    # Routers
    application.include_router(v1_router, prefix="/api")

    # Exception handlers
    register_exception_handlers(application)

    return application


app = create_application()
