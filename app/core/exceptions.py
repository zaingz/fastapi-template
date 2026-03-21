class AppException(Exception):  # noqa: N818
    """Base exception for all application exceptions."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "An internal error occurred"

    def __init__(self, message: str | None = None, details: dict | None = None) -> None:
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


class UnauthorizedError(AppException):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppException):
    status_code = 403
    code = "FORBIDDEN"


class RateLimitError(AppException):
    status_code = 429
    code = "RATE_LIMITED"
    message = "Too many requests"
