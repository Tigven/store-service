from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.repositories.store import StoreRepository
from app.schemas import ItemKind, PlayerOut, StoreItemOut

router = APIRouter(prefix="/v1/store", tags=["store"])


def get_repo(request: Request) -> StoreRepository:
    return request.app.state.store_repo


@router.get("/items", response_model=list[StoreItemOut])
async def list_items(
    kind: ItemKind | None = None,
    repo: StoreRepository = Depends(get_repo),
) -> list[StoreItemOut]:
    items = await repo.list_items(kind)
    return [StoreItemOut(**asdict(item)) for item in items]


@router.get("/players/{player_id}", response_model=PlayerOut)
async def get_player(
    player_id: UUID,
    repo: StoreRepository = Depends(get_repo),
) -> PlayerOut:
    player = await repo.get_player(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="player_not_found")
    return PlayerOut(**asdict(player))
