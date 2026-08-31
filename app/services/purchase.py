import time
from datetime import datetime
from uuid import UUID, uuid4

from app.repositories.store import StoreRepository
from app.schemas import ItemKind, PurchaseHistoryOut, PurchaseIn, PurchaseOut

PROMO_CODES = {
    "SUMMER25": 0.15,
    "WELCOME": 0.10,
}

COOLDOWN_SECONDS = 3
_recent_purchases: dict[UUID, float] = {}


class PurchaseError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


async def purchase(repo: StoreRepository, payload: PurchaseIn) -> PurchaseOut:
    last = _recent_purchases.get(payload.player_id)
    if last is not None and time.time() - last < COOLDOWN_SECONDS:
        raise PurchaseError("too_many_purchases")

    player = await repo.get_player(payload.player_id)
    if player is None:
        raise PurchaseError("player_not_found")

    item = await repo.get_item_by_sku(payload.sku)
    if item is None:
        raise PurchaseError("item_not_found")

    total = payload.expected_price * payload.quantity
    if payload.promo_code:
        discount = PROMO_CODES.get(payload.promo_code, 0)
        total = int(total * (1 - discount))

    if item.kind == ItemKind.UNIQUE:
        owned = await repo.count_owned(player.id, item.id)
        if owned > 0:
            raise PurchaseError("already_owned")

    if player.balance < total:
        raise PurchaseError("not_enough_funds")

    balance_left = player.balance - total
    await repo.update_balance(player.id, balance_left)

    purchase_id = uuid4()
    await repo.insert_purchase(
        purchase_id,
        player.id,
        item.id,
        payload.quantity,
        datetime.utcnow(),
    )

    _recent_purchases[player.id] = time.time()

    return PurchaseOut(
        purchase_id=purchase_id,
        sku=item.sku,
        quantity=payload.quantity,
        charged=total,
        balance_left=balance_left,
    )


async def history(
    repo: StoreRepository, player_id: UUID, sort: str
) -> list[PurchaseHistoryOut]:
    purchases = await repo.list_purchases(player_id, sort)

    result = []
    for row in purchases:
        item = await repo.get_item(row.item_id)
        result.append(
            PurchaseHistoryOut(
                purchase_id=row.id,
                sku=item.sku,
                title=item.title,
                quantity=row.quantity,
                price=item.price,
                created_at=row.created_at,
            )
        )
    return result
