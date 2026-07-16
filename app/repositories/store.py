from __future__ import annotations

from dataclasses import dataclass
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


def _item(row: asyncpg.Record) -> StoreItem:
    return StoreItem(
        id=row["id"],
        sku=row["sku"],
        title=row["title"],
        price=row["price"],
        kind=ItemKind(row["kind"]),
    )
