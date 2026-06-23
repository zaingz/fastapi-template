CHAT_URL = "/api/v1/chat/"
STREAM_URL = "/api/v1/chat/stream"


async def test_chat_completion_echoes_user_message(async_client):
    response = await async_client.post(
        CHAT_URL, json={"messages": [{"role": "user", "content": "hello world"}]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "Echo: hello world"
    assert body["model"] == "echo-1"
    assert body["cached"] is False


async def test_chat_completion_second_identical_request_is_cached(async_client):
    payload = {"messages": [{"role": "user", "content": "cache me"}]}

    first = await async_client.post(CHAT_URL, json=payload)
    second = await async_client.post(CHAT_URL, json=payload)

    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert first.json()["content"] == second.json()["content"]


async def test_chat_completion_rejects_empty_messages(async_client):
    response = await async_client.post(CHAT_URL, json={"messages": []})
    assert response.status_code == 422


async def test_chat_stream_emits_start_tokens_done(async_client):
    response = await async_client.post(
        STREAM_URL, json={"messages": [{"role": "user", "content": "stream this"}]}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-store"

    events = [line for line in response.text.splitlines() if line.startswith("event:")]
    assert events[0] == "event: start"
    assert events[-1] == "event: done"
    assert "event: token" in events
