from structlog.testing import capture_logs


async def test_one_access_log_per_request_with_fields(async_client):
    with capture_logs() as logs:
        response = await async_client.get("/api/v1/health/")
    assert response.status_code == 200

    access = [entry for entry in logs if entry.get("event") == "request"]
    assert len(access) == 1
    entry = access[0]
    assert entry["method"] == "GET"
    assert entry["path"] == "/api/v1/health/"
    assert entry["status"] == 200
    assert isinstance(entry["duration_ms"], float)
    assert "request_id" in entry


async def test_request_id_bound_into_nested_logs(async_client):
    # The correlation id is exposed to the client and should match the access log.
    with capture_logs() as logs:
        response = await async_client.get("/api/v1/health/")
    access = next(entry for entry in logs if entry.get("event") == "request")
    assert response.headers["X-Request-ID"] == access["request_id"]
