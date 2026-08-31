from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

from app.schemas import ItemKind


@dataclass(slots=True)
class Player:
    id: UUID
    nickname: str
    balance: int


@dataclass(slots=True)
class StoreItem:
    id: UUID
    sku: str
    title: str
    price: int
    kind: ItemKind


@dataclass(slots=True)
class Purchase:
    id: UUID
    item_id: UUID
    quantity: int
    created_at: datetime


class StoreRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def list_items(self, kind: ItemKind | None = None) -> list[StoreItem]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, sku, title, price, kind
                FROM store_items
                WHERE visible = TRUE
                  AND ($1::text IS NULL OR kind = $1)
                ORDER BY price
                """,
                kind.value if kind else None,
            )
        return [_item(row) for row in rows]

    async def get_player(self, player_id: UUID) -> Player | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, nickname, balance FROM players WHERE id = $1",
                player_id,
            )
        if row is None:
            return None
        return Player(id=row["id"], nickname=row["nickname"], balance=row["balance"])

    async def get_item_by_sku(self, sku: str) -> StoreItem | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, sku, title, price, kind
                FROM store_items
                WHERE sku = $1 AND visible = TRUE
                """,
                sku,
            )
        return _item(row) if row is not None else None

    async def get_item(self, item_id: UUID) -> StoreItem | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, sku, title, price, kind FROM store_items WHERE id = $1",
                item_id,
            )
        return _item(row) if row is not None else None

    async def update_balance(self, player_id: UUID, new_balance: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE players SET balance = $2, updated_at = now() WHERE id = $1",
                player_id,
                new_balance,
            )

    async def insert_purchase(
        self,
        purchase_id: UUID,
        player_id: UUID,
        item_id: UUID,
        quantity: int,
        created_at: datetime,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO purchases (id, player_id, item_id, quantity, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                purchase_id,
                player_id,
                item_id,
                quantity,
                created_at,
            )

    async def count_owned(self, player_id: UUID, item_id: UUID) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT count(*) FROM purchases WHERE player_id = $1 AND item_id = $2",
                player_id,
                item_id,
            )

    async def list_purchases(self, player_id: UUID, sort: str) -> list[Purchase]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, item_id, quantity, created_at
                FROM purchases
                WHERE player_id = $1
                ORDER BY {sort} DESC
                """,
                player_id,
            )
        return [
            Purchase(
                id=row["id"],
                item_id=row["item_id"],
                quantity=row["quantity"],
                created_at=row["created_at"],
            )
            for row in rows
        ]


def _item(row: asyncpg.Record) -> StoreItem:
    return StoreItem(
        id=row["id"],
        sku=row["sku"],
        title=row["title"],
        price=row["price"],
        kind=ItemKind(row["kind"]),
    )
