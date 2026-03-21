async def test_list_items_empty(async_client):
    response = await async_client.get("/api/v1/items/")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_create_item(async_client):
    payload = {"name": "Widget", "description": "A fine widget", "price": 9.99}
    response = await async_client.post("/api/v1/items/", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Widget"
    assert body["price"] == 9.99
    assert "id" in body


async def test_get_item(async_client):
    # Create first
    create_resp = await async_client.post("/api/v1/items/", json={"name": "Gadget", "price": 19.99})
    item_id = create_resp.json()["id"]

    # Get
    response = await async_client.get(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Gadget"


async def test_get_item_not_found(async_client):
    response = await async_client.get("/api/v1/items/nonexistent")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "NOT_FOUND"


async def test_update_item(async_client):
    create_resp = await async_client.post("/api/v1/items/", json={"name": "Old Name", "price": 5.0})
    item_id = create_resp.json()["id"]

    response = await async_client.patch(f"/api/v1/items/{item_id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["price"] == 5.0


async def test_delete_item(async_client):
    create_resp = await async_client.post("/api/v1/items/", json={"name": "Doomed", "price": 1.0})
    item_id = create_resp.json()["id"]

    response = await async_client.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 204

    # Verify gone
    get_resp = await async_client.get(f"/api/v1/items/{item_id}")
    assert get_resp.status_code == 404
