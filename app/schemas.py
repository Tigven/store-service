from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


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


class PurchaseRequest(BaseModel):
    item_id: UUID
    expected_price: int = Field(ge=0)
    idempotency_key: str = Field(min_length=8, max_length=64)


class PurchaseResponse(BaseModel):
    purchase_id: UUID
    item_id: UUID
    price_paid: int
    balance_after: int


class RefundResponse(BaseModel):
    purchase_id: UUID
    refunded: int
    balance_after: int
