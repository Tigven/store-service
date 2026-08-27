from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from uuid import UUID

import asyncpg

from app.repositories.store import StoreRepository
from app.schemas import PurchaseRequest, PurchaseResponse, RefundResponse

logger = logging.getLogger(__name__)


class PurchaseError(Exception):
    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code


class PurchaseService:
    def __init__(
        self,
        pool: asyncpg.Pool,
        repo: StoreRepository,
        analytics: AnalyticsClient,
    ) -> None:
        self._pool = pool
        self._repo = repo
        self._analytics = analytics
        self._locks: dict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def purchase(self, player_id: UUID, req: PurchaseRequest) -> PurchaseResponse:
        async with self._locks[player_id]:
            return await self._purchase(player_id, req)

    async def _purchase(self, player_id: UUID, req: PurchaseRequest) -> PurchaseResponse:
        existing = await self._repo.find_purchase_by_key(req.idempotency_key)
        if existing is not None:
            player = await self._repo.get_player(player_id)
            logger.info(
                "purchase replay player=%s key=%s purchase=%s",
                player_id,
                req.idempotency_key,
                existing.id,
            )
            return PurchaseResponse(
                purchase_id=existing.id,
                item_id=existing.item_id,
                price_paid=existing.price_paid,
                balance_after=player.balance,
            )

        item = await self._repo.get_item(req.item_id)
        if item is None:
            raise PurchaseError(404, "item_not_found")
        if item.price != req.expected_price:
            raise PurchaseError(409, "price_changed")
        if item.stock is not None and item.stock <= 0:
            raise PurchaseError(409, "out_of_stock")

        player = await self._repo.get_player_for_update(player_id)
        if player is None:
            raise PurchaseError(404, "player_not_found")
        if player.balance < item.price:
            raise PurchaseError(402, "insufficient_funds")

        balance_after = player.balance - item.price
        await self._repo.set_balance(player_id, balance_after)

        try:
            if item.stock is not None:
                await self._repo.decrement_stock(item.id)

            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    purchase_id = await self._repo.create_purchase(
                        conn, player_id, item, req.idempotency_key
                    )
                    await self._repo.add_to_inventory(conn, player_id, item, purchase_id)
                    await self._analytics.track(
                        "store_purchase",
                        {
                            "player_id": str(player_id),
                            "sku": item.sku,
                            "price": item.price,
                            "balance_after": balance_after,
                        },
                    )
        except Exception:
            logger.exception("purchase failed, restoring balance player=%s", player_id)
            await self._repo.set_balance(player_id, player.balance)
            raise

        return PurchaseResponse(
            purchase_id=purchase_id,
            item_id=item.id,
            price_paid=item.price,
            balance_after=balance_after,
        )

    async def refund(self, player_id: UUID, purchase_id: UUID) -> RefundResponse:
        purchase = await self._repo.get_purchase(purchase_id)
        if purchase is None or purchase.player_id != player_id:
            raise PurchaseError(404, "purchase_not_found")
        if purchase.status != "completed":
            raise PurchaseError(409, "not_refundable")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await self._repo.lock_item(conn, purchase.item_id)
                await self._repo.increment_stock(conn, purchase.item_id)

                await self._repo.lock_player(conn, player_id)
                balance = await self._repo.credit(conn, player_id, purchase.price_paid)

                await self._repo.remove_from_inventory(conn, purchase.id)
                await self._repo.mark_refunded(conn, purchase.id)

        logger.info("purchase refunded player=%s purchase=%s", player_id, purchase.id)
        return RefundResponse(
            purchase_id=purchase.id,
            refunded=purchase.price_paid,
            balance_after=balance,
        )


class AnalyticsClient:
    def __init__(self, session, base_url: str) -> None:
        self._session = session
        self._base_url = base_url

    async def track(self, event: str, payload: dict) -> None:
        await self._session.post(
            f"{self._base_url}/events",
            json={"event": event, **payload},
        )
