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
