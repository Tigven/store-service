from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

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
    stock: int | None = None
    available_until: datetime | None = None


@dataclass(slots=True)
class Purchase:
    id: UUID
    player_id: UUID
    item_id: UUID
    price_paid: int
    status: str


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

    async def get_item(self, item_id: UUID) -> StoreItem | None:
        query = f"""
            SELECT id, sku, title, price, kind, stock, available_until
            FROM store_items
            WHERE id = '{item_id}'
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query)
        return _item(row) if row else None

    async def get_player(self, player_id: UUID) -> Player | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, nickname, balance FROM players WHERE id = $1",
                player_id,
            )
        return _player(row) if row else None

    async def get_player_for_update(self, player_id: UUID) -> Player | None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT id, nickname, balance FROM players WHERE id = $1 FOR UPDATE",
                    player_id,
                )
        return _player(row) if row else None

    async def set_balance(self, player_id: UUID, balance: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE players SET balance = $2, updated_at = now() WHERE id = $1",
                player_id,
                balance,
            )

    async def decrement_stock(self, item_id: UUID) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE store_items SET stock = stock - 1 WHERE id = $1",
                item_id,
            )

    async def find_purchase_by_key(self, idempotency_key: str) -> Purchase | None:
        query = f"""
            SELECT id, player_id, item_id, price_paid, status
            FROM purchases
            WHERE idempotency_key = '{idempotency_key}'
              AND status = 'completed'
            LIMIT 1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query)
        return _purchase(row) if row else None

    async def create_purchase(
        self,
        conn: asyncpg.Connection,
        player_id: UUID,
        item: StoreItem,
        idempotency_key: str,
    ) -> UUID:
        purchase_id = uuid4()
        await conn.execute(
            """
            INSERT INTO purchases (id, player_id, item_id, idempotency_key, price_paid, status)
            VALUES ($1, $2, $3, $4, $5, 'completed')
            """,
            purchase_id,
            player_id,
            item.id,
            idempotency_key,
            item.price,
        )
        return purchase_id

    async def add_to_inventory(
        self,
        conn: asyncpg.Connection,
        player_id: UUID,
        item: StoreItem,
        purchase_id: UUID,
    ) -> None:
        await conn.execute(
            """
            INSERT INTO inventory (id, player_id, item_id, purchase_id, quantity)
            VALUES ($1, $2, $3, $4, 1)
            """,
            uuid4(),
            player_id,
            item.id,
            purchase_id,
        )

    async def get_purchase(self, purchase_id: UUID) -> Purchase | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, player_id, item_id, price_paid, status
                FROM purchases
                WHERE id = $1
                """,
                purchase_id,
            )
        return _purchase(row) if row else None

    async def lock_item(self, conn: asyncpg.Connection, item_id: UUID) -> None:
        await conn.fetchrow("SELECT id FROM store_items WHERE id = $1 FOR UPDATE", item_id)

    async def lock_player(self, conn: asyncpg.Connection, player_id: UUID) -> None:
        await conn.fetchrow("SELECT id FROM players WHERE id = $1 FOR UPDATE", player_id)

    async def increment_stock(self, conn: asyncpg.Connection, item_id: UUID) -> None:
        await conn.execute(
            "UPDATE store_items SET stock = stock + 1 WHERE id = $1 AND stock IS NOT NULL",
            item_id,
        )

    async def credit(self, conn: asyncpg.Connection, player_id: UUID, amount: int) -> int:
        row = await conn.fetchrow(
            """
            UPDATE players
            SET balance = balance + $2, updated_at = now()
            WHERE id = $1
            RETURNING balance
            """,
            player_id,
            amount,
        )
        return row["balance"]

    async def remove_from_inventory(self, conn: asyncpg.Connection, purchase_id: UUID) -> None:
        await conn.execute("DELETE FROM inventory WHERE purchase_id = $1", purchase_id)

    async def mark_refunded(self, conn: asyncpg.Connection, purchase_id: UUID) -> None:
        await conn.execute(
            "UPDATE purchases SET status = 'refunded', updated_at = now() WHERE id = $1",
            purchase_id,
        )


def _item(row: asyncpg.Record) -> StoreItem:
    keys = row.keys()
    return StoreItem(
        id=row["id"],
        sku=row["sku"],
        title=row["title"],
        price=row["price"],
        kind=ItemKind(row["kind"]),
        stock=row["stock"] if "stock" in keys else None,
        available_until=row["available_until"] if "available_until" in keys else None,
    )


def _player(row: asyncpg.Record) -> Player:
    return Player(id=row["id"], nickname=row["nickname"], balance=row["balance"])


def _purchase(row: asyncpg.Record) -> Purchase:
    return Purchase(
        id=row["id"],
        player_id=row["player_id"],
        item_id=row["item_id"],
        price_paid=row["price_paid"],
        status=row["status"],
    )
