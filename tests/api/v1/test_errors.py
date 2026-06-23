async def test_not_found_error_body_includes_request_id(async_client):
    response = await async_client.get("/api/v1/items/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "NOT_FOUND"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert set(body) >= {"error", "message", "details", "timestamp", "path", "request_id"}


async def test_validation_error_body_includes_request_id(async_client):
    response = await async_client.post("/api/v1/chat/", json={"messages": []})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "VALIDATION_FAILED"
    assert body["request_id"] == response.headers["X-Request-ID"]
