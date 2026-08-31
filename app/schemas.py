from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class ItemKind(StrEnum):
    CONSUMABLE = "consumable"
    UNIQUE = "unique"


class StoreItemOut(BaseModel):
    id: UUID
    sku: str
    title: str
    price: int
    kind: ItemKind


class PlayerOut(BaseModel):
    id: UUID
    nickname: str
    balance: int


class PurchaseIn(BaseModel):
    player_id: UUID
    sku: str
    quantity: int = 1
    expected_price: int
    promo_code: str | None = None


class PurchaseOut(BaseModel):
    purchase_id: UUID
    sku: str
    quantity: int
    charged: int
    balance_left: int


class PurchaseHistoryOut(BaseModel):
    purchase_id: UUID
    sku: str
    title: str
    quantity: int
    price: int
    created_at: datetime
