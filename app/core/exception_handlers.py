import math
from datetime import UTC, datetime
from typing import Any

import structlog
from asgi_correlation_id import correlation_id
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.exceptions import AppException, RateLimitError, UpstreamRateLimitError
from app.core.security_headers import build_security_headers

logger = structlog.get_logger(__name__)


def _error_body(
    error: str,
    message: str,
    details: dict[str, Any] | list[Any] | None,
    path: str,
) -> dict[str, Any]:
    return {
        "error": error,
        "message": message,
        "details": details or {},
        "timestamp": datetime.now(UTC).isoformat(),
        "path": path,
        # Bound to the correlation id so a client error can be traced to its log line.
        "request_id": correlation_id.get(),
    }


def error_json_response(
    *,
    status_code: int,
    code: str,
    message: str,
    path: str,
    details: dict[str, Any] | list[Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the uniform error response. Shared with middleware that runs outside the
    exception-handler stack and so cannot rely on AppException conversion."""
    return JSONResponse(
        status_code=status_code,
        content=_error_body(code, message, details, path),
        headers=headers,
    )


def _retry_after_header(exc: AppException) -> dict[str, str]:
    retry_after = getattr(exc, "retry_after", None)
    if retry_after is None:
        return {}
    # HTTP Retry-After is an integer number of seconds; round up so a sub-second hint
    # (e.g. 0.5s) never truncates to 0 and tells the client to retry immediately.
    return {"Retry-After": str(max(1, math.ceil(retry_after)))}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        headers = (
            _retry_after_header(exc)
            if isinstance(exc, RateLimitError | UpstreamRateLimitError)
            else {}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details, str(request.url.path)),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "VALIDATION_FAILED",
                "Request validation failed",
                list(exc.errors()),
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
        logger.exception("Unhandled exception", path=request.url.path)
        # This handler runs in Starlette's ServerErrorMiddleware, *outside* the user
        # middleware stack, so neither SecurityHeadersMiddleware nor CorrelationIdMiddleware
        # sees this response. Re-stamp both here so the "every response" guarantees
        # (security headers + X-Request-ID echo) hold for unhandled 500s too.
        settings = get_settings()
        headers = build_security_headers(settings) if settings.SECURITY_HEADERS_ENABLED else {}
        request_id = correlation_id.get()
        if request_id is not None:
            headers["X-Request-ID"] = request_id
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "INTERNAL_ERROR",
                "An internal error occurred",
                None,
                str(request.url.path),
            ),
            headers=headers,
        )
