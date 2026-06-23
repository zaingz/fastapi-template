import time

import structlog
from asgi_correlation_id import correlation_id
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("app.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Emits exactly one structured access log per request and binds `request_id`
    into the structlog contextvars so every log within the request carries it.

    Must run inside CorrelationIdMiddleware so the correlation id is already set.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = correlation_id.get()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )
        structlog.contextvars.unbind_contextvars("request_id")
        return response
