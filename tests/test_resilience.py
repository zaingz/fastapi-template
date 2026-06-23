import httpx
import pytest

from app.core.exceptions import (
    UpstreamError,
    UpstreamRateLimitError,
    UpstreamTimeoutError,
)
from app.core.resilience import (
    classify_httpx_exception,
    raise_for_upstream,
    retry_async,
)


def _response(status: int, headers: dict[str, str] | None = None) -> httpx.Response:
    request = httpx.Request("GET", "https://upstream.test/x")
    return httpx.Response(status, headers=headers or {}, request=request)


def test_raise_for_upstream_passes_through_2xx():
    response = _response(200)
    assert raise_for_upstream(response) is response


def test_raise_for_upstream_429_is_rate_limit_with_retry_after():
    with pytest.raises(UpstreamRateLimitError) as exc:
        raise_for_upstream(_response(429, {"Retry-After": "7"}))
    assert exc.value.retry_after == 7.0


@pytest.mark.parametrize("status", [502, 503, 504])
def test_raise_for_upstream_transient_5xx(status):
    with pytest.raises(UpstreamTimeoutError):
        raise_for_upstream(_response(status))


def test_raise_for_upstream_400_is_non_retryable():
    with pytest.raises(UpstreamError) as exc:
        raise_for_upstream(_response(400))
    assert not isinstance(exc.value, UpstreamTimeoutError | UpstreamRateLimitError)


def test_classify_timeout_is_transient():
    classified = classify_httpx_exception(httpx.ReadTimeout("slow"))
    assert isinstance(classified, UpstreamTimeoutError)


def test_classify_protocol_error_is_non_retryable():
    classified = classify_httpx_exception(httpx.RemoteProtocolError("bad frame"))
    assert isinstance(classified, UpstreamError)
    assert not isinstance(classified, UpstreamTimeoutError)


async def test_retry_async_retries_transient_then_succeeds():
    calls = 0

    async def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise UpstreamTimeoutError()
        return "ok"

    result = await retry_async(flaky, retries=3, base_delay=0.0, max_delay=0.0)
    assert result == "ok"
    assert calls == 3


async def test_retry_async_does_not_retry_non_transient():
    calls = 0

    async def boom() -> str:
        nonlocal calls
        calls += 1
        raise UpstreamError()

    with pytest.raises(UpstreamError):
        await retry_async(boom, retries=3, base_delay=0.0, max_delay=0.0)
    assert calls == 1  # no blanket retry


async def test_retry_async_exhausts_then_raises():
    async def always_timeout() -> str:
        raise UpstreamTimeoutError()

    with pytest.raises(UpstreamTimeoutError):
        await retry_async(always_timeout, retries=2, base_delay=0.0, max_delay=0.0)
