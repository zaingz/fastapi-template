from app.core.config import Settings


def build_security_headers(settings: Settings) -> dict[str, str]:
    """Conservative security response headers, derived once from settings.

    Shared by SecurityHeadersMiddleware (the normal response path) and the catch-all
    exception handler (unhandled 500s render in Starlette's ServerErrorMiddleware, which
    sits *outside* user middleware, so the middleware never sees that response).
    """
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": f"frame-ancestors {settings.CSP_FRAME_ANCESTORS}",
        "Referrer-Policy": settings.REFERRER_POLICY,
        "Permissions-Policy": settings.PERMISSIONS_POLICY,
    }
    if settings.HSTS_ENABLED:
        headers["Strict-Transport-Security"] = f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains"
    return headers
