import os
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.repositories.store import StoreRepository

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgres://store:store@localhost:5432/store"
)
MIGRATIONS = sorted(Path("migrations").glob("*.sql"))


@pytest.fixture
async def pool():
    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS purchases, players, store_items")
        for migration in MIGRATIONS:
            await conn.execute(migration.read_text())
    yield pool
    await pool.close()


@pytest.fixture
async def seed(pool):
    player_id, potion_id, skin_id = uuid4(), uuid4(), uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO players (id, nickname, balance) VALUES ($1, 'tester', 500)",
            player_id,
        )
        await conn.execute(
            """
            INSERT INTO store_items (id, sku, title, price, kind) VALUES
                ($1, 'potion_small', 'Small potion', 25, 'consumable'),
                ($2, 'skin_dragon_01', 'Dragon skin', 100, 'unique')
            """,
            potion_id,
            skin_id,
        )
    return {"player_id": player_id, "potion_id": potion_id, "skin_id": skin_id}


@pytest.fixture
async def client(pool):
    app.state.pool = pool
    app.state.store_repo = StoreRepository(pool)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
