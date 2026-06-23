from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Sets conservative security response headers on every response.

    Headers are computed once from settings and reused. HSTS is opt-in (HTTPS only);
    framing is denied via CSP `frame-ancestors` rather than the legacy X-Frame-Options
    alone, but both are sent for older clients.
    """

    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._headers = self._build(settings)

    @staticmethod
    def _build(settings: Settings) -> dict[str, str]:
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": f"frame-ancestors {settings.CSP_FRAME_ANCESTORS}",
            "Referrer-Policy": settings.REFERRER_POLICY,
            "Permissions-Policy": settings.PERMISSIONS_POLICY,
        }
        if settings.HSTS_ENABLED:
            headers["Strict-Transport-Security"] = (
                f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains"
            )
        return headers

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for key, value in self._headers.items():
            response.headers.setdefault(key, value)
        return response
