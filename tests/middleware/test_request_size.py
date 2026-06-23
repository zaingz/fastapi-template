CHAT_URL = "/api/v1/chat/"


async def test_oversized_content_length_returns_413(async_client):
    # Declare a body far over the 1 MiB default cap via Content-Length.
    headers = {"Content-Length": str(2 * 1_048_576), "Content-Type": "application/json"}
    response = await async_client.post(CHAT_URL, content=b"{}", headers=headers)
    assert response.status_code == 413
    body = response.json()
    assert body["error"] == "REQUEST_TOO_LARGE"
    assert body["details"]["max_bytes"] == 1_048_576
    assert "request_id" in body


async def test_normal_request_passes_size_check(async_client):
    response = await async_client.post(
        CHAT_URL, json={"messages": [{"role": "user", "content": "hi"}]}
    )
    assert response.status_code == 200
