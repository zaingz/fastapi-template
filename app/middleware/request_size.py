from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.exception_handlers import error_json_response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects oversized request bodies with a uniform 413.

    Enforced via the `Content-Length` header — the standard signal clients send. Bodies
    without a declared length (chunked transfer) are bounded by the ASGI server's own
    limits; document those for streaming-upload endpoints.

    ponytail: header check only. For byte-exact enforcement on chunked uploads, wrap the
    ASGI `receive` callable to count bytes — added complexity most APIs don't need.
    """

    def __init__(self, app: object, max_bytes: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                declared = -1
            if declared > self._max_bytes:
                return error_json_response(
                    status_code=413,
                    code="REQUEST_TOO_LARGE",
                    message=f"Request body exceeds {self._max_bytes} bytes",
                    path=request.url.path,
                    details={"max_bytes": self._max_bytes, "content_length": declared},
                )
        return await call_next(request)
