import asyncio
import random
from collections.abc import Awaitable, Callable

import httpx
import structlog

from app.core.exceptions import (
    UpstreamError,
    UpstreamRateLimitError,
    UpstreamTimeoutError,
)

logger = structlog.get_logger(__name__)

# Status codes that are safe to retry (transient). 4xx other than 429 are caller errors.
_TRANSIENT_STATUS = {429, 502, 503, 504}


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # delta-seconds form; HTTP-date form is not honored here
    except ValueError:
        return None


def raise_for_upstream(response: httpx.Response) -> httpx.Response:
    """Map a downstream HTTP response to the upstream taxonomy. Returns the response on 2xx/3xx.

    Only 429/502/503/504 become *transient* (retryable) exceptions; other 4xx/5xx raise a
    non-retryable UpstreamError so we never blindly retry caller errors.
    """
    if response.status_code < 400:
        return response
    if response.status_code == 429:
        raise UpstreamRateLimitError(
            message=f"Upstream returned 429 ({response.request.url})",
            retry_after=_parse_retry_after(response.headers.get("Retry-After")),
        )
    if response.status_code in _TRANSIENT_STATUS:
        raise UpstreamTimeoutError(
            message=f"Upstream returned {response.status_code} ({response.request.url})"
        )
    raise UpstreamError(
        message=f"Upstream returned {response.status_code} ({response.request.url})",
        details={"status_code": response.status_code},
    )


def classify_httpx_exception(exc: httpx.HTTPError) -> UpstreamError:
    """Translate transport-level httpx errors into the upstream taxonomy.

    Timeouts and connection errors are transient; everything else is a non-retryable
    UpstreamError. Never classify arbitrary exceptions as retryable.
    """
    if isinstance(exc, httpx.TimeoutException):
        return UpstreamTimeoutError(message=f"Upstream request timed out: {exc!r}")
    if isinstance(exc, httpx.ConnectError | httpx.NetworkError):
        return UpstreamTimeoutError(message=f"Upstream connection failed: {exc!r}")
    return UpstreamError(message=f"Upstream request failed: {exc!r}")


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, UpstreamTimeoutError | UpstreamRateLimitError)


async def retry_async[T](
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int = 2,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
) -> T:
    """Run an async operation, retrying ONLY classified transient upstream failures.

    Backoff is exponential with full jitter. A transient exception carrying `retry_after`
    (e.g. a 429) waits at least that long. Non-transient exceptions propagate immediately —
    there is no blanket `except Exception` retry.

    ponytail: stdlib backoff, no extra dep. For richer policies (circuit breakers, deadline
    budgets) drop in `tenacity`/`stamina` as an optional extra — see docs/recipes/.
    """
    attempt = 0
    while True:
        try:
            return await operation()
        except UpstreamError as exc:
            if not _is_transient(exc) or attempt >= retries:
                raise
            delay = min(max_delay, base_delay * (2**attempt))
            delay = random.uniform(0, delay)  # noqa: S311 — jitter, not crypto
            retry_after = getattr(exc, "retry_after", None)
            if retry_after is not None:
                delay = max(delay, float(retry_after))
            logger.info(
                "retrying upstream call",
                attempt=attempt + 1,
                retries=retries,
                delay_s=round(delay, 3),
                code=exc.code,
            )
            await asyncio.sleep(delay)
            attempt += 1
