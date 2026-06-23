from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.exception_handlers import error_json_response
from app.core.rate_limit import RateLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies a per-client rate limit, keyed by client IP.

    Disabled unless wired in (only added when `RATE_LIMIT_ENABLED`). On limit breach
    returns a uniform 429 with `Retry-After`. The default limiter is in-process; use a
    shared backend for multi-instance correctness (see docs).
    """

    def __init__(self, app: object, limiter: RateLimiter) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._limiter = limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        key = request.client.host if request.client else "anonymous"
        decision = await self._limiter.acquire(key)
        if not decision.allowed:
            return error_json_response(
                status_code=429,
                code="RATE_LIMITED",
                message="Rate limit exceeded",
                path=request.url.path,
                details={"retry_after": decision.retry_after},
                headers={"Retry-After": str(decision.retry_after)},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        return response
