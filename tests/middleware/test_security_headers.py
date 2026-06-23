async def test_security_headers_present_on_every_response(async_client):
    response = await async_client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["Permissions-Policy"]


async def test_hsts_absent_when_disabled(async_client):
    # Default test settings keep HSTS off (local HTTP).
    response = await async_client.get("/api/v1/health/")
    assert "Strict-Transport-Security" not in response.headers
