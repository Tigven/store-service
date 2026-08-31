from uuid import uuid4

import pytest

from app.repositories.store import Player, Purchase, StoreItem
from app.schemas import ItemKind, PurchaseIn
from app.services import purchase as purchase_service


class FakeRepo:
    def __init__(self, player, items):
        self.player = player
        self.by_sku = {item.sku: item for item in items}
        self.by_id = {item.id: item for item in items}
        self.purchases: list[Purchase] = []

    async def get_player(self, player_id):
        return self.player if self.player.id == player_id else None

    async def get_item_by_sku(self, sku):
        return self.by_sku.get(sku)

    async def get_item(self, item_id):
        return self.by_id.get(item_id)

    async def update_balance(self, player_id, new_balance):
        self.player.balance = new_balance

    async def insert_purchase(self, purchase_id, player_id, item_id, quantity, created_at):
        self.purchases.append(
            Purchase(
                id=purchase_id,
                item_id=item_id,
                quantity=quantity,
                created_at=created_at,
            )
        )

    async def count_owned(self, player_id, item_id):
        return sum(1 for row in self.purchases if row.item_id == item_id)

    async def list_purchases(self, player_id, sort):
        return list(reversed(self.purchases))


@pytest.fixture(autouse=True)
def _reset_cooldown():
    purchase_service._recent_purchases.clear()


@pytest.fixture
def potion():
    return StoreItem(
        id=uuid4(),
        sku="potion_small",
        title="Small potion",
        price=25,
        kind=ItemKind.CONSUMABLE,
    )


@pytest.fixture
def skin():
    return StoreItem(
        id=uuid4(),
        sku="skin_dragon_01",
        title="Dragon skin",
        price=100,
        kind=ItemKind.UNIQUE,
    )


@pytest.fixture
def repo(potion, skin):
    return FakeRepo(
        player=Player(id=uuid4(), nickname="tester", balance=500),
        items=[potion, skin],
    )


async def test_purchase_debits_balance(repo):
    result = await purchase_service.purchase(
        repo,
        PurchaseIn(
            player_id=repo.player.id,
            sku="potion_small",
            quantity=2,
            expected_price=25,
        ),
    )
    assert result.charged == 50
    assert result.balance_left == 450
    assert repo.player.balance == 450
    assert len(repo.purchases) == 1


async def test_purchase_applies_promo_code(repo):
    result = await purchase_service.purchase(
        repo,
        PurchaseIn(
            player_id=repo.player.id,
            sku="skin_dragon_01",
            expected_price=100,
            promo_code="SUMMER25",
        ),
    )
    assert result.charged == 85
    assert repo.player.balance == 415


async def test_purchase_without_funds(repo):
    repo.player.balance = 10
    with pytest.raises(purchase_service.PurchaseError) as exc:
        await purchase_service.purchase(
            repo,
            PurchaseIn(
                player_id=repo.player.id,
                sku="potion_small",
                expected_price=25,
            ),
        )
    assert exc.value.code == "not_enough_funds"


async def test_unique_item_cannot_be_bought_twice(repo):
    payload = PurchaseIn(
        player_id=repo.player.id,
        sku="skin_dragon_01",
        expected_price=100,
    )
    await purchase_service.purchase(repo, payload)

    purchase_service._recent_purchases.clear()

    with pytest.raises(purchase_service.PurchaseError) as exc:
        await purchase_service.purchase(repo, payload)
    assert exc.value.code == "already_owned"


async def test_history_returns_item_titles(repo):
    await purchase_service.purchase(
        repo,
        PurchaseIn(
            player_id=repo.player.id,
            sku="potion_small",
            expected_price=25,
        ),
    )
    rows = await purchase_service.history(repo, repo.player.id, "created_at")
    assert [row.title for row in rows] == ["Small potion"]
    assert rows[0].price == 25
