from dataclasses import asdict
from uuid import uuid4

import pytest

from app.repositories.store import Player, StoreItem
from app.schemas import ItemKind, PlayerOut, StoreItemOut


class FakeRepo:
    def __init__(self, items, player):
        self._items = items
        self._player = player

    async def list_items(self, kind=None):
        if kind is None:
            return self._items
        return [item for item in self._items if item.kind == kind]

    async def get_player(self, player_id):
        return self._player if self._player and self._player.id == player_id else None


@pytest.fixture
def repo():
    return FakeRepo(
        items=[
            StoreItem(
                id=uuid4(),
                sku="potion_small",
                title="Small potion",
                price=25,
                kind=ItemKind.CONSUMABLE,
            ),
            StoreItem(
                id=uuid4(),
                sku="skin_dragon_01",
                title="Dragon skin",
                price=100,
                kind=ItemKind.UNIQUE,
            ),
        ],
        player=Player(id=uuid4(), nickname="tester", balance=500),
    )


async def test_list_items_returns_all(repo):
    items = await repo.list_items()
    assert len(items) == 2
    assert StoreItemOut(**asdict(items[0])).price == 25


async def test_list_items_filters_by_kind(repo):
    items = await repo.list_items(ItemKind.UNIQUE)
    assert [item.sku for item in items] == ["skin_dragon_01"]


async def test_get_player(repo):
    player = await repo.get_player(repo._player.id)
    assert PlayerOut(**asdict(player)).balance == 500


async def test_get_unknown_player(repo):
    assert await repo.get_player(uuid4()) is None
