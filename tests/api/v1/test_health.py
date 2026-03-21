async def test_health_returns_200(async_client):
    response = await async_client.get("/api/v1/health/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "environment" in body


async def test_ready_returns_200(async_client):
    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "checks" in body
