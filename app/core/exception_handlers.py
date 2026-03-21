import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def _error_body(
    error: str,
    message: str,
    details: dict | list | None,
    path: str,
) -> dict:
    return {
        "error": error,
        "message": message,
        "details": details or {},
        "timestamp": datetime.now(UTC).isoformat(),
        "path": path,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details, str(request.url.path)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "VALIDATION_FAILED",
                "Request validation failed",
                exc.errors(),
                str(request.url.path),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(
                f"HTTP_{exc.status_code}",
                str(exc.detail),
                None,
                str(request.url.path),
            ),
        )

    @app.exception_handler(Exception)
    async def global_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "INTERNAL_ERROR",
                "An internal error occurred",
                None,
                str(request.url.path),
            ),
        )
