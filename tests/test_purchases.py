async def balance_of(pool, player_id):
    return await pool.fetchval("SELECT balance FROM players WHERE id = $1", player_id)


async def test_buy_item(client, pool, seed):
    response = await client.post(
        "/v1/store/purchases",
        json={
            "player_id": str(seed["player_id"]),
            "sku": "potion_small",
            "price": 25,
            "quantity": 2,
        },
    )
    body = response.json()

    assert body["charged"] == 50
    assert body["balance_left"] == 450
    assert await balance_of(pool, seed["player_id"]) == 450


async def test_buy_unique_item_twice(client, pool, seed):
    payload = {
        "player_id": str(seed["player_id"]),
        "sku": "skin_dragon_01",
        "price": 100,
    }
    first = await client.post("/v1/store/purchases", json=payload)
    assert first.json()["charged"] == 100

    second = await client.post("/v1/store/purchases", json=payload)
    assert second.json()["detail"] == "already_owned"

    assert await balance_of(pool, seed["player_id"]) == 400


async def test_buy_without_enough_funds(client, pool, seed):
    response = await client.post(
        "/v1/store/purchases",
        json={
            "player_id": str(seed["player_id"]),
            "sku": "skin_dragon_01",
            "price": 100,
            "quantity": 10,
        },
    )

    assert response.json()["detail"] == "not_enough_funds"
    assert await balance_of(pool, seed["player_id"]) == 500


async def test_buy_unknown_item(client, seed):
    response = await client.post(
        "/v1/store/purchases",
        json={
            "player_id": str(seed["player_id"]),
            "sku": "nope",
            "price": 1,
        },
    )

    assert response.json()["detail"] == "item_not_found"
