from typing import Any


class AppException(Exception):  # noqa: N818
    """Base exception for all application exceptions."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "An internal error occurred"

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(message=f"{resource} '{identifier}' not found")


class ConflictError(AppException):
    status_code = 409
    code = "CONFLICT"


class ValidationError(AppException):
    status_code = 422
    code = "VALIDATION_FAILED"


class RequestTooLargeError(AppException):
    status_code = 413
    code = "REQUEST_TOO_LARGE"
    message = "Request body too large"


class RateLimitError(AppException):
    """Raised when a caller exceeds the configured rate limit.

    `retry_after` (seconds) is surfaced as a `Retry-After` response header.
    """

    status_code = 429
    code = "RATE_LIMITED"
    message = "Rate limit exceeded"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        *,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message=message, details=details)
        self.retry_after = retry_after


# ── Downstream / upstream taxonomy ────────────────────────────────────────────
# Failures calling other services. Only *transient* subclasses are safe to retry;
# see app/core/resilience.py for the classification used by the retry helper.


class UpstreamError(AppException):
    """A downstream/upstream dependency call failed. Not retryable by default."""

    status_code = 502
    code = "UPSTREAM_ERROR"
    message = "A downstream service returned an error"


class UpstreamTimeoutError(UpstreamError):
    """Downstream call exceeded its timeout. Transient — safe to retry."""

    status_code = 504
    code = "UPSTREAM_TIMEOUT"
    message = "A downstream service did not respond in time"


class UpstreamRateLimitError(UpstreamError):
    """Downstream returned 429. Transient — retry honoring Retry-After."""

    status_code = 429
    code = "UPSTREAM_RATE_LIMITED"
    message = "A downstream service rate-limited the request"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        *,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message=message, details=details)
        self.retry_after = retry_after
