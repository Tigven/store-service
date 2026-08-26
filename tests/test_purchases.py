import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from app.repositories.store import Player, Purchase, StoreItem
from app.schemas import ItemKind, PurchaseRequest
from app.services.purchase_service import PurchaseError, PurchaseService

PLAYER_ID = uuid4()
ITEM_ID = uuid4()


class FakeRepo:
    def __init__(self, balance: int, stock: int | None):
        self.player = Player(id=PLAYER_ID, nickname="tester", balance=balance)
        self.item = StoreItem(
            id=ITEM_ID,
            sku="skin_dragon_01",
            title="Скин «Дракон»",
            price=100,
            kind=ItemKind.UNIQUE,
            stock=stock,
        )
        self.purchases: dict[str, Purchase] = {}
        self.inventory: list[tuple] = []

    async def get_item(self, item_id):
        return self.item if item_id == self.item.id else None

    async def get_player(self, player_id):
        return self.player if player_id == self.player.id else None

    async def get_player_for_update(self, player_id):
        return self.player if player_id == self.player.id else None

    async def set_balance(self, player_id, balance):
        self.player.balance = balance

    async def decrement_stock(self, item_id):
        self.item.stock -= 1

    async def find_purchase_by_key(self, key):
        return self.purchases.get(key)

    async def create_purchase(self, conn, player_id, item, key):
        purchase_id = uuid4()
        self.purchases[key] = Purchase(
            id=purchase_id,
            player_id=player_id,
            item_id=item.id,
            price_paid=item.price,
            status="completed",
        )
        return purchase_id

    async def add_to_inventory(self, conn, player_id, item, purchase_id):
        self.inventory.append((player_id, item.id, purchase_id))


class FakeConn:
    @asynccontextmanager
    async def transaction(self):
        yield


class FakePool:
    @asynccontextmanager
    async def acquire(self):
        yield FakeConn()


class FakeAnalytics:
    def __init__(self):
        self.events = []

    async def track(self, event, payload):
        self.events.append((event, payload))


def make_service(balance=1000, stock=5):
    repo = FakeRepo(balance=balance, stock=stock)
    return PurchaseService(FakePool(), repo, FakeAnalytics()), repo


def request(key="idem-key-0001"):
    return PurchaseRequest(item_id=ITEM_ID, expected_price=100, idempotency_key=key)


async def test_purchase_debits_balance_and_grants_item():
    service, repo = make_service()

    result = await service.purchase(PLAYER_ID, request())

    assert result.price_paid == 100
    assert result.balance_after == 900
    assert repo.player.balance == 900
    assert len(repo.inventory) == 1


async def test_purchase_decrements_stock():
    service, repo = make_service(stock=1)

    await service.purchase(PLAYER_ID, request())

    assert repo.item.stock == 0


async def test_unlimited_item_keeps_null_stock():
    service, repo = make_service(stock=None)

    await service.purchase(PLAYER_ID, request())

    assert repo.item.stock is None


async def test_out_of_stock():
    service, _ = make_service(stock=0)

    with pytest.raises(PurchaseError) as exc:
        await service.purchase(PLAYER_ID, request())

    assert exc.value.status_code == 409
    assert exc.value.code == "out_of_stock"


async def test_insufficient_funds_keeps_balance():
    service, repo = make_service(balance=50)

    with pytest.raises(PurchaseError) as exc:
        await service.purchase(PLAYER_ID, request())

    assert exc.value.status_code == 402
    assert repo.player.balance == 50


async def test_price_changed():
    service, repo = make_service()
    repo.item.price = 150

    with pytest.raises(PurchaseError) as exc:
        await service.purchase(PLAYER_ID, request())

    assert exc.value.code == "price_changed"


async def test_retry_with_same_key_does_not_charge_twice():
    service, repo = make_service()

    first = await service.purchase(PLAYER_ID, request())
    second = await service.purchase(PLAYER_ID, request())

    assert first.purchase_id == second.purchase_id
    assert repo.player.balance == 900
    assert len(repo.inventory) == 1


async def test_concurrent_purchases_are_serialized():
    service, repo = make_service(balance=1000, stock=10)

    await asyncio.gather(
        *[service.purchase(PLAYER_ID, request(key=f"idem-key-{i:04d}")) for i in range(5)]
    )

    assert repo.player.balance == 500
    assert repo.item.stock == 5
    assert len(repo.inventory) == 5
