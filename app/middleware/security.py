from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.core.security_headers import build_security_headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Sets conservative security response headers on every routed response.

    Headers are computed once from settings and reused. HSTS is opt-in (HTTPS only);
    framing is denied via CSP `frame-ancestors` rather than the legacy X-Frame-Options
    alone, but both are sent for older clients. Unhandled 500s are stamped by the
    catch-all exception handler (which runs outside this middleware) using the same
    `build_security_headers` source, so the guarantee holds on every response.
    """

    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._headers = build_security_headers(settings)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for key, value in self._headers.items():
            response.headers.setdefault(key, value)
        return response
